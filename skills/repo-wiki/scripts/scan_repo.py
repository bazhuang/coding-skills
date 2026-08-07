#!/usr/bin/env python3
"""Scan a local repository and output file tree + README content as JSON.

Git-aware scan input governance for the repo-wiki skill.

Scan algorithm:
  1. If <repo_path> is a git repository, build the source file list from
     `git ls-files` (tracked files) instead of walking the whole directory.
     Optionally include untracked-but-whitelisted doc files with
     --include-untracked. If git commands fail, fall back to an os.walk.
  2. Exclusions are applied on top of either source list:
       - wiki output / backup / skill-temp directories (from config)
       - build & IDE caches (from config)
       - sensitive files (.env, keys, certs, credentials) -- counted and
         excluded so their content never reaches prompts or artifacts
  3. Symlink policy controls directory traversal in walk mode:
       - skip:          never follow symlinks
       - internal-only: follow only symlinks whose real path stays inside
                        the repo root (default); with cycle detection
       - follow:        follow all symlinks; with cycle detection
  4. Deterministic file selection: root README is chosen by a fixed priority
     list, not by directory-walk order.

Output JSON fields:
  repo_path      -- absolute source path
  branch         -- git branch (empty if not a git repo)
  git_commit     -- HEAD commit sha (empty if not a git repo)
  git_hash       -- same as git_commit (back-compat alias used by export_wiki.py)
  dirty          -- True if the working tree has uncommitted changes
  scan_mode      -- "git" | "walk"
  symlink_policy -- one of the accepted symlink values
  file_tree      -- sorted newline-joined list of repo-relative paths
  file_hashes    -- {rel_path: sha256-16} for every kept file
  readme         -- root README content if present, else ""
  excluded_paths -- list of {path, reason} for excluded directories/files
  sensitive_file_count -- number of sensitive files excluded

Usage:
    python3 scan_repo.py <repo_path> [--output <output.json>]
        [--allow-dir <path>] [--allow-file <glob>]
        [--symlinks {skip,internal-only,follow}]
        [--include-untracked]

If --output is omitted, prints JSON to stdout.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import sys


# --------------------------------------------------------------------------- #
# Built-in defaults (overridable via references/scan-excludes.json)
# --------------------------------------------------------------------------- #
_BUILTIN_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".idea", ".vscode", "dist", "build", ".next", "target",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

# Wiki output / backup / skill-temp dirs: matched as relative path prefixes.
_BUILTIN_WIKI_OUTPUT_DIRS = [
    ".qoder/repowiki", "docs/wiki", "zcode-wiki", "docs-bak", ".repo-wiki",
]

_BUILTIN_EXCLUDED_SUFFIXES = (
    ".pyc", ".pyo", ".class", ".o", ".so", ".dylib", ".dll", ".exe",
)

_BUILTIN_EXCLUDED_NAMES = {".DS_Store", "Thumbs.db", ".gitignore", ".gitkeep"}

# Matched against basename via fnmatch.
_BUILTIN_SENSITIVE_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.crt",
    "*.keystore", "*.jks", "id_rsa", "id_rsa.pub", "id_ed25519",
    "id_ed25519.pub", "credentials", "credentials.json",
    "secrets", "secrets.json", "*.secret",
]

_BUILTIN_README_NAMES = [
    "README.md", "readme.md", "README.MD", "Readme.md", "README",
    "README.txt", "readme.txt",
]


def _builtin_config() -> dict:
    return {
        "excluded_dirs": sorted(_BUILTIN_EXCLUDED_DIRS),
        "wiki_output_dirs": list(_BUILTIN_WIKI_OUTPUT_DIRS),
        "excluded_file_suffixes": list(_BUILTIN_EXCLUDED_SUFFIXES),
        "excluded_file_names": sorted(_BUILTIN_EXCLUDED_NAMES),
        "sensitive_file_patterns": list(_BUILTIN_SENSITIVE_PATTERNS),
        "deterministic_readme_names": list(_BUILTIN_README_NAMES),
    }


def load_config(config_path: str | None = None) -> dict:
    """Load exclusion config from JSON file; merge over built-in defaults."""
    cfg = _builtin_config()
    if not config_path or not os.path.isfile(config_path):
        return cfg
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in cfg:
            if isinstance(data.get(key), list):
                cfg[key] = data[key]
    except Exception as e:
        print(f"Warning: failed to read config {config_path}: {e}", file=sys.stderr)
    return cfg


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #
def _git(repo_path: str, *args: str, timeout: int = 15) -> str | None:
    """Run git in repo_path; return stripped stdout or None on failure."""
    try:
        r = subprocess.run(
            ["git", *args], cwd=repo_path,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def get_git_info(repo_path: str) -> dict:
    """Return {branch, commit, dirty, is_git}."""
    is_git = _git(repo_path, "rev-parse", "--is-inside-work-tree") == "true"
    if not is_git:
        return {"branch": "", "commit": "", "dirty": False, "is_git": False}
    branch = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD") or ""
    commit = _git(repo_path, "rev-parse", "HEAD") or ""
    status = _git(repo_path, "status", "--porcelain")
    dirty = bool(status)
    return {"branch": branch, "commit": commit, "dirty": dirty, "is_git": True}


def git_tracked_files(repo_path: str, include_untracked: bool) -> list[str] | None:
    """Return tracked (+ optionally whitelisted untracked) file list, or None."""
    out = _git(repo_path, "ls-files", "-z")
    if out is None:
        return None
    files = [p for p in out.split("\0") if p]
    if include_untracked:
        extra = _git(repo_path, "ls-files", "-z", "--others", "--exclude-standard")
        if extra:
            files.extend(p for p in extra.split("\0") if p)
    return [f.replace(os.sep, "/") for f in files]


# --------------------------------------------------------------------------- #
# Filesystem walk with symlink policy + cycle detection
# --------------------------------------------------------------------------- #
def _is_within(child_real: str, parent_real: str) -> bool:
    """True if child_real is inside or equal to parent_real."""
    try:
        return os.path.commonpath([child_real, parent_real]) == parent_real
    except ValueError:
        return False


def _is_wiki_or_excluded_dir(rel_d: str, d: str,
                              excluded_dirs: set[str],
                              wiki_prefixes: list[str]) -> str | None:
    """Return reason string if dir should be excluded, else None."""
    if d in excluded_dirs:
        return "excluded_dir"
    for p in wiki_prefixes:
        if rel_d == p or rel_d.startswith(p + "/"):
            return "wiki_output"
    return None


def walk_files(repo_path: str, symlink_policy: str, cfg: dict,
               allow_dirs: list[str], allow_files: list[str]
               ) -> tuple[list[str], list[dict]]:
    """Walk repo directory tree. Returns (files, excluded_paths)."""
    repo_real = os.path.realpath(repo_path)
    excluded_dirs = set(cfg["excluded_dirs"])
    wiki_prefixes = [p.rstrip("/") for p in cfg["wiki_output_dirs"] if p]
    suffixes = tuple(cfg["excluded_file_suffixes"])
    names = set(cfg["excluded_file_names"])

    def _allowed(rel: str) -> bool:
        for ad in allow_dirs:
            adn = ad.replace("\\", "/").rstrip("/")
            if rel == adn or rel.startswith(adn + "/"):
                return True
        return any(fnmatch.fnmatch(os.path.basename(rel), pat) for pat in allow_files)

    files: list[str] = []
    excluded: list[dict] = []
    visited_real: set[str] = set()
    followlinks = symlink_policy in ("internal-only", "follow")

    for root, dirs, fnames in os.walk(repo_path, topdown=True, followlinks=followlinks):
        rel_root = os.path.relpath(root, repo_path).replace(os.sep, "/")
        rel_root = "" if rel_root == "." else rel_root
        real_root = os.path.realpath(root)

        if real_root in visited_real:
            dirs[:] = []
            continue
        visited_real.add(real_root)

        # --- filter directories ---
        kept: list[str] = []
        for d in sorted(dirs):
            rel_d = f"{rel_root}/{d}" if rel_root else d
            if _allowed(rel_d):
                kept.append(d)
                continue
            reason = _is_wiki_or_excluded_dir(rel_d, d, excluded_dirs, wiki_prefixes)
            if reason:
                excluded.append({"path": rel_d, "reason": reason})
                continue
            abs_d = os.path.join(root, d)
            if os.path.islink(abs_d):
                real_d = os.path.realpath(abs_d)
                if symlink_policy == "skip":
                    excluded.append({"path": rel_d, "reason": "symlink_skipped"})
                    continue
                if symlink_policy == "internal-only" and not _is_within(real_d, repo_real):
                    excluded.append({"path": rel_d, "reason": "symlink_outside_root"})
                    continue
            kept.append(d)
        dirs[:] = kept

        # --- files ---
        for fname in sorted(fnames):
            rel_f = f"{rel_root}/{fname}" if rel_root else fname
            if _allowed(rel_f):
                files.append(rel_f)
                continue
            if fname in names:
                excluded.append({"path": rel_f, "reason": "excluded_name"})
                continue
            if any(fname.endswith(s) for s in suffixes):
                excluded.append({"path": rel_f, "reason": "excluded_suffix"})
                continue
            files.append(rel_f)

    return files, excluded


# --------------------------------------------------------------------------- #
# Sensitive file filtering
# --------------------------------------------------------------------------- #
def filter_sensitive(files: list[str], cfg: dict) -> tuple[list[str], int]:
    """Split (kept, sensitive_count) using basename fnmatch."""
    patterns = cfg["sensitive_file_patterns"]
    kept = []
    count = 0
    for f in files:
        if any(fnmatch.fnmatch(os.path.basename(f), pat) for pat in patterns):
            count += 1
        else:
            kept.append(f)
    return kept, count


# --------------------------------------------------------------------------- #
# Hashing + README
# --------------------------------------------------------------------------- #
def compute_file_hash(file_path: str) -> str:
    """SHA-256 of file content, first 16 hex chars."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()[:16]


def find_readme(repo_path: str, files: list[str], cfg: dict) -> str:
    """Read root README by deterministic priority list."""
    root_basenames = {os.path.basename(f): f for f in files if "/" not in f}
    for name in cfg["deterministic_readme_names"]:
        if name in root_basenames:
            try:
                with open(os.path.join(repo_path, root_basenames[name]),
                          "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                pass
    for f in sorted(files):
        if "/" not in f and os.path.basename(f).lower().startswith("readme"):
            try:
                with open(os.path.join(repo_path, f),
                          "r", encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except Exception:
                pass
    return ""


# --------------------------------------------------------------------------- #
# Main scan
# --------------------------------------------------------------------------- #
def scan_repo(repo_path: str, config_path: str | None = None,
              allow_dirs: list[str] | None = None,
              allow_files: list[str] | None = None,
              symlink_policy: str = "internal-only",
              include_untracked: bool = False) -> dict:
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    allow_dirs = allow_dirs or []
    allow_files = allow_files or []
    git_info = get_git_info(repo_path)

    scan_mode = "walk"
    files: list[str] = []
    excluded: list[dict] = []

    # 1. Build raw candidate list
    if git_info["is_git"]:
        tracked = git_tracked_files(repo_path, include_untracked)
        if tracked is not None:
            files = tracked
            scan_mode = "git"

    if scan_mode == "walk":
        files, excluded = walk_files(repo_path, symlink_policy, cfg,
                                      allow_dirs, allow_files)

    # 2. Apply directory/wiki exclusions in git mode too
    if scan_mode == "git":
        excluded_dirs = set(cfg["excluded_dirs"])
        wiki_prefixes = [p.rstrip("/") for p in cfg["wiki_output_dirs"] if p]

        def _allowed(rel: str) -> bool:
            for ad in allow_dirs:
                adn = ad.replace("\\", "/").rstrip("/")
                if rel == adn or rel.startswith(adn + "/"):
                    return True
            return any(fnmatch.fnmatch(os.path.basename(rel), pat) for pat in allow_files)

        kept: list[str] = []
        for f in files:
            if _allowed(f):
                kept.append(f)
                continue
            top = f.split("/", 1)[0]
            if top in excluded_dirs:
                excluded.append({"path": top, "reason": "excluded_dir"})
                continue
            matched = next((p for p in wiki_prefixes
                           if f == p or f.startswith(p + "/")), None)
            if matched:
                excluded.append({"path": matched, "reason": "wiki_output"})
                continue
            # Also check nested excluded dirs (e.g. target/ inside a module)
            parts = f.split("/")
            for i in range(len(parts) - 1):
                if parts[i] in excluded_dirs:
                    excluded.append({"path": "/".join(parts[:i+1]), "reason": "excluded_dir"})
                    break
            else:
                kept.append(f)
        files = kept

    # 3. Sensitive files: exclude + count, never hash
    files, sensitive_count = filter_sensitive(files, cfg)
    if sensitive_count:
        print(f"Warning: excluded {sensitive_count} sensitive file(s)", file=sys.stderr)

    # 4. Deterministic order + hashing
    files = sorted(set(files))
    file_hashes: dict[str, str] = {}
    for rel in files:
        file_hashes[rel] = compute_file_hash(os.path.join(repo_path, rel))

    readme = find_readme(repo_path, files, cfg)

    return {
        "repo_path": repo_path,
        "branch": git_info["branch"],
        "git_commit": git_info["commit"],
        "git_hash": git_info["commit"],  # back-compat
        "dirty": git_info["dirty"],
        "scan_mode": scan_mode,
        "symlink_policy": symlink_policy,
        "file_tree": "\n".join(files),
        "file_hashes": file_hashes,
        "readme": readme,
        "excluded_paths": excluded,
        "sensitive_file_count": sensitive_count,
    }


def _default_config_path() -> str | None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(script_dir, "..", "references", "scan-excludes.json"))
    return candidate if os.path.isfile(candidate) else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a local repo and output file tree + README as JSON")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON file path (default: stdout)")
    parser.add_argument("--config", default=None,
                        help="Path to scan-excludes.json")
    parser.add_argument("--allow-dir", action="append", default=None,
                        help="Re-include a directory prefix (repeatable)")
    parser.add_argument("--allow-file", action="append", default=None,
                        help="Re-include files matching this fnmatch glob (repeatable)")
    parser.add_argument("--symlinks", choices=("skip", "internal-only", "follow"),
                        default="internal-only",
                        help="Symlink traversal policy (default: internal-only)")
    parser.add_argument("--include-untracked", action="store_true",
                        help="Include untracked-but-not-gitignored files in git mode")
    args = parser.parse_args()

    result = scan_repo(
        args.repo_path,
        config_path=args.config or _default_config_path(),
        allow_dirs=args.allow_dir,
        allow_files=args.allow_file,
        symlink_policy=args.symlinks,
        include_untracked=args.include_untracked,
    )

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
