#!/usr/bin/env python3
"""Scan a repository for multi-module structure boundaries.

Module boundaries come from what the project authors DECLARED in their
build files -- not from heuristics on package names or class-name
suffixes. Supported build systems (treated equally, first match wins):

  - Maven            pom.xml with <modules>
  - Gradle           settings.gradle(.kts) include ':x'
  - Cargo workspace  Cargo.toml [workspace] members
  - Go work          go.work use ./x
  - npm workspaces   package.json "workspaces"
  - pnpm workspace   pnpm-workspace.yaml packages
  - Lerna            lerna.json packages
  - Nx               per-project project.json "name"

Output JSON drives two things in the wiki skill:
  1. "deep mode" structure generation (the module tree is the skeleton)
  2. module-level incremental updates (scope dirs map files -> modules)

A single-module or unrecognised project yields multi_module:false and
the skill falls back to comprehensive mode without breaking.

The business-logic splitting of large leaf modules (e.g. one artifact
that holds several sub-domains) is intentionally NOT done here -- it is
language/stack-specific. The script reports each leaf's file count so
that the structure-generation step (an LLM) can refine big leaves into
multiple documentation pages by reading the file tree.

Usage:
    python3 scan_modules.py <repo_path> [--output <out.json>]
                                      [--scan <scan.json>]
                                      [--format json|text]

If --output is omitted, prints to stdout.
--scan reuses the file list from scan_repo.py to avoid a second walk.
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import glob as _glob
import json
import os
import re
import sys
from xml.etree import ElementTree as ET


# Same exclusions as scan_repo.py / scan_api_entries.py (duplicated to keep
# this script standalone with zero cross-file dependencies).
EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".idea", ".vscode", "dist", "build", ".next", "target",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}
EXCLUDED_FILE_SUFFIXES = (".pyc", ".pyo", ".class", ".o", ".so", ".dylib", ".dll", ".exe")
EXCLUDED_FILE_NAMES = {".DS_Store", "Thumbs.db", ".gitignore", ".gitkeep"}

# A leaf module with more than this many files is reported as "large" so the
# structure-generation step knows to consider splitting it into several pages.
LARGE_LEAF_THRESHOLD = 50


# --------------------------------------------------------------------------- #
# File collection
# --------------------------------------------------------------------------- #
def _walk_files(repo_path: str) -> list[str]:
    """Return repo-relative file paths (forward slashes), respecting excludes."""
    repo_path = os.path.abspath(repo_path)
    files: list[str] = []
    for root, dirs, fnames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in sorted(fnames):
            if fname in EXCLUDED_FILE_NAMES:
                continue
            if any(fname.endswith(suf) for suf in EXCLUDED_FILE_SUFFIXES):
                continue
            rel = os.path.relpath(os.path.join(root, fname), repo_path).replace(os.sep, "/")
            files.append(rel)
    return files


def _collect_files(repo_path: str, scan_path: str | None) -> list[str]:
    """Get the repo file list, reusing scan_repo.py output when available."""
    if scan_path and os.path.isfile(scan_path):
        try:
            with open(scan_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tree = data.get("file_tree", "")
            if isinstance(tree, str) and tree.strip():
                return [ln for ln in tree.splitlines() if ln.strip()]
        except Exception:
            pass  # fall back to walking
    return _walk_files(repo_path)


# --------------------------------------------------------------------------- #
# Build-system detectors
# Each returns (build_system_name, nodes) or None.
# A node is {"path": <rel dir, "." for root>, "name": <str>, "parent_path": <or None>, "refined": bool}.
# --------------------------------------------------------------------------- #
def _detect_maven(repo_path: str):
    """Maven multi-module via <modules> in pom.xml (recursive)."""
    root_pom = os.path.join(repo_path, "pom.xml")
    if not os.path.isfile(root_pom):
        return None

    nodes: list[dict] = []
    visited: set[str] = set()

    def _parse(pom_path: str) -> ET.Element | None:
        try:
            with open(pom_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            # Strip default xmlns so we can findtext("artifactId") etc.
            text = re.sub(r'\sxmlns="[^"]+"', "", text, count=1)
            text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
            return ET.fromstring(text)
        except Exception:
            return None

    def _walk(pom_abs: str, mod_rel_dir: str, parent_path: str | None):
        root = _parse(pom_abs)
        if root is None:
            return
        artifact_id = (root.findtext("artifactId") or "").strip()
        name = artifact_id or os.path.basename(mod_rel_dir.rstrip("/")) or "root"
        node_path = mod_rel_dir if mod_rel_dir else "."
        nodes.append({"path": node_path, "name": name, "parent_path": parent_path, "refined": False})

        modules_el = root.find("modules")
        if modules_el is None:
            return
        for m in modules_el.findall("module"):
            child_val = (m.text or "").strip()
            if not child_val:
                continue
            child_rel = os.path.normpath(os.path.join(mod_rel_dir, child_val)).replace(os.sep, "/")
            child_pom = os.path.join(repo_path, child_rel, "pom.xml")
            if child_pom in visited or not os.path.isfile(child_pom):
                continue
            visited.add(child_pom)
            _walk(child_pom, child_rel, node_path)

    visited.add(root_pom)
    _walk(root_pom, "", None)
    if not nodes:
        return None
    return ("maven", nodes)


def _detect_gradle(repo_path: str):
    """Gradle via settings.gradle(.kts) include directives."""
    for fname in ("settings.gradle.kts", "settings.gradle"):
        path = os.path.join(repo_path, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            continue
        # An include directive can list several projects on one line:
        #   include 'app', 'lib', 'core'
        # or appear as a call / block:
        #   include('app', 'lib')
        includes: list[str] = []
        for inc_line in text.splitlines():
            # find "include ..." on this line and harvest every quoted token after it
            mm = re.search(r"\binclude\b(.*)", inc_line)
            if not mm:
                continue
            tail = mm.group(1)
            # stop at a trailing comment
            tail = re.split(r"//|#", tail)[0]
            for a, b in re.findall(r'"([^"]+)"|\'([^\']+)\'', tail):
                val = (a or b).strip()
                if val:
                    includes.append(val)
        if not includes:
            continue
        nodes: list[dict] = []
        node_paths: set[str] = set()

        def _ensure(parts: list[str]):
            # Create this node and any missing ancestor aggregate nodes.
            for depth in range(1, len(parts) + 1):
                seg = parts[:depth]
                p = "/".join(seg)
                if p in node_paths:
                    continue
                parent = "/".join(seg[:-1]) if len(seg) > 1 else "."
                if parent != "." and parent not in node_paths:
                    # ensure ancestor recorded (it will be created by shorter depth)
                    pass
                nodes.append({"path": p, "name": seg[-1], "parent_path": parent, "refined": False})
                node_paths.add(p)

        for inc in includes:
            # Gradle project paths use ':' as the hierarchy separator
            # (e.g. "services:auth" -> dir services/auth). Normalise both
            # ':' and '\' to '/' so the path maps to the filesystem.
            norm = inc.replace(":", "/").replace("\\", "/")
            parts = [p for p in norm.split("/") if p and p != "."]
            if not parts:
                continue
            _ensure(parts)
        if not nodes:
            continue
        # Root aggregator (only if not already present).
        if "." not in node_paths:
            nodes.insert(0, {"path": ".", "name": os.path.basename(repo_path) or "root",
                             "parent_path": None, "refined": False})
            node_paths.add(".")
        return ("gradle", nodes)
    return None


def _detect_cargo(repo_path: str):
    """Cargo workspace via [workspace] members in Cargo.toml."""
    path = os.path.join(repo_path, "Cargo.toml")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    members = _toml_workspace_members(text)
    if not members:
        return None
    return _build_glob_modules(repo_path, members, "cargo")


def _toml_workspace_members(text: str) -> list[str]:
    """Extract `members = [...]` (and exclude = [...]) from the [workspace] section."""
    lines = text.splitlines()
    in_ws = False
    members: list[str] = []
    in_members = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_ws = stripped == "[workspace]"
            in_members = False
            continue
        if not in_ws:
            continue
        if stripped.startswith("members"):
            # members = [ "a", "b" ] possibly on one line
            rest = stripped.split("=", 1)[1] if "=" in stripped else ""
            members.extend(_toml_string_list(rest))
            in_members = not rest.rstrip().endswith("]")
            continue
        if in_members:
            if stripped.endswith("]"):
                in_members = False
            members.extend(_toml_string_list(stripped))
    return [m for m in members if m]


def _toml_string_list(s: str) -> list[str]:
    """Extract quoted string values from a TOML list fragment."""
    return [a or b for a, b in re.findall(r'"([^"]+)"|\'([^\']+)\'', s)]


def _detect_go_work(repo_path: str):
    """Go workspace via `use ./x` directives in go.work."""
    path = os.path.join(repo_path, "go.work")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    dirs: list[str] = []
    # single-line: use ./a, ./b ; or block: use (\n ./a \n ./b \n)
    for m in re.finditer(r"use\s+([^\n]+)", text):
        rest = m.group(1)
        # stop at a closing paren if it's a block opener on same line
        for tok in rest.split():
            tok = tok.strip().strip("()")
            if tok and not tok.startswith("("):
                dirs.append(tok)
    # block form across lines: lines starting with ./ inside a use ( ) block
    for line in text.splitlines():
        s = line.strip().strip("()")
        if s.startswith("./"):
            dirs.append(s)
    dirs = sorted({d.lstrip("./").replace("\\", "/").strip("/") for d in dirs if d})
    dirs = [d for d in dirs if d]
    if not dirs:
        return None
    nodes = [{"path": ".", "name": os.path.basename(repo_path) or "root", "parent_path": None, "refined": False}]
    for d in dirs:
        nodes.append({"path": d, "name": os.path.basename(d), "parent_path": ".", "refined": False})
    return ("go-work", nodes)


def _detect_npm_workspaces(repo_path: str):
    """npm workspaces via package.json "workspaces"."""
    path = os.path.join(repo_path, "package.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return None
    ws = data.get("workspaces")
    patterns: list[str] = []
    if isinstance(ws, list):
        patterns = [p for p in ws if isinstance(p, str)]
    elif isinstance(ws, dict):
        patterns = [p for p in (ws.get("packages") or []) if isinstance(p, str)]
    if not patterns:
        return None
    return _build_glob_modules(repo_path, patterns, "npm-workspaces", root_name=data.get("name"))


def _detect_pnpm(repo_path: str):
    """pnpm workspace via pnpm-workspace.yaml packages."""
    path = os.path.join(repo_path, "pnpm-workspace.yaml")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    patterns: list[str] = []
    in_packages = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("packages:"):
            in_packages = True
            continue
        if in_packages:
            # A new top-level key ends the list.
            if line and not line.startswith((" ", "\t", "-")) and ":" in s and not s.startswith("-"):
                in_packages = False
                continue
            if s.startswith("-"):
                val = s.lstrip("-").strip().strip('"').strip("'")
                if val:
                    patterns.append(val)
    if not patterns:
        return None
    return _build_glob_modules(repo_path, patterns, "pnpm-workspace")


def _detect_lerna(repo_path: str):
    """Lerna via lerna.json packages."""
    path = os.path.join(repo_path, "lerna.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return None
    patterns = [p for p in (data.get("packages") or []) if isinstance(p, str)]
    if not patterns:
        return None
    return _build_glob_modules(repo_path, patterns, "lerna")


def _detect_nx(repo_path: str):
    """Nx via per-project project.json files declaring a "name"."""
    if not os.path.isfile(os.path.join(repo_path, "nx.json")):
        return None
    nodes: list[dict] = []
    node_paths: set[str] = set()
    for root, dirs, fnames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        if "project.json" in fnames:
            try:
                with open(os.path.join(root, "project.json"), "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
            except Exception:
                continue
            name = data.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            rel = os.path.relpath(root, repo_path).replace(os.sep, "/")
            rel = "." if rel == "." else rel
            if rel in node_paths:
                continue
            nodes.append({"path": rel, "name": name, "parent_path": None, "refined": False})
            node_paths.add(rel)
    if len(nodes) < 2:
        return None
    # Root aggregator to hold top-level projects.
    nodes.insert(0, {"path": ".", "name": os.path.basename(repo_path) or "root", "parent_path": None, "refined": False})
    # Attach each non-root project to the root (Nx projects are typically flat).
    for n in nodes[1:]:
        n["parent_path"] = "."
    return ("nx", nodes)


def _build_glob_modules(repo_path: str, patterns: list[str], build_system: str, root_name: str | None = None):
    """Expand workspace glob patterns into module nodes."""
    dirs = _expand_globs(repo_path, patterns)
    dirs = {d for d in dirs if d and d != "."}
    if len(dirs) < 2:
        return None  # a single workspace dir is not really "multi-module"
    root = root_name or os.path.basename(repo_path) or "root"
    nodes = [{"path": ".", "name": root, "parent_path": None, "refined": False}]
    for d in sorted(dirs):
        nodes.append({"path": d, "name": os.path.basename(d), "parent_path": ".", "refined": False})
    return (build_system, nodes)


def _expand_globs(repo_path: str, patterns: list[str]) -> set[str]:
    """Expand workspace glob patterns (e.g. packages/*) to relative dirs."""
    result: set[str] = set()
    for pat in patterns:
        pat = pat.strip().strip('"').strip("'")
        if not pat:
            continue
        for match in _glob.glob(os.path.join(repo_path, pat), recursive=True):
            if os.path.isdir(match):
                rel = os.path.relpath(match, repo_path).replace(os.sep, "/")
                if rel != ".":
                    result.add(rel)
    return result


# --------------------------------------------------------------------------- #
# Module enrichment: depends_on, runtime_role, source/test counts, entry points
# --------------------------------------------------------------------------- #
def _compute_depends_on(mod_path: str, node: dict, by_path: dict,
                        id_by_path: dict, repo_path: str,
                        mod_files: list[str], build_system: str) -> dict:
    """Compute inter-module dependencies from build files and source imports.

    Returns {"depends_on": [module_id,...], "evidence": [{from, to, signal}]}.
    Only strong signals (declared build-file deps) are added to depends_on.
    Weak signals (source-level imports) are recorded as evidence only.
    """
    deps: list[str] = []
    evidence: list[dict] = []
    mod_id = id_by_path.get(mod_path, mod_path)

    # Build artifact_id -> module_id lookup for Maven
    artifact_to_id: dict[str, str] = {}
    if build_system == "maven":
        for p, n in by_path.items():
            # Parse artifactId from pom.xml if available
            pom = os.path.join(repo_path, p, "pom.xml") if p != "." else os.path.join(repo_path, "pom.xml")
            if os.path.isfile(pom):
                try:
                    with open(pom, "r", encoding="utf-8", errors="replace") as f:
                        text = re.sub(r'\sxmlns="[^"]+"', "", f.read(), count=1)
                        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
                    root = ET.fromstring(text)
                    aid = (root.findtext("artifactId") or "").strip()
                    if aid:
                        artifact_to_id[aid] = id_by_path.get(p, p)
                except Exception:
                    pass

    # --- Maven: scan <dependency><artifactId>X</artifactId> in this module's pom ---
    if build_system == "maven":
        pom = os.path.join(repo_path, mod_path, "pom.xml") if mod_path != "." else os.path.join(repo_path, "pom.xml")
        if os.path.isfile(pom):
            try:
                with open(pom, "r", encoding="utf-8", errors="replace") as f:
                    text = re.sub(r'\sxmlns="[^"]+"', "", f.read(), count=1)
                    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
                root = ET.fromstring(text)
                deps_el = root.find("dependencies")
                if deps_el is not None:
                    for dep in deps_el.findall("dependency"):
                        aid = (dep.findtext("artifactId") or "").strip()
                        if aid and aid in artifact_to_id:
                            target_id = artifact_to_id[aid]
                            if target_id != mod_id and target_id not in deps:
                                deps.append(target_id)
                                evidence.append({"from": mod_id, "to": target_id,
                                                 "signal": f"maven:<dependency>{aid}</dependency>"})
            except Exception:
                pass

    # --- Gradle: scan implementation project(':X') ---
    if build_system == "gradle":
        for fpath in mod_files:
            if not fpath.endswith((".gradle", ".gradle.kts")):
                continue
            try:
                with open(os.path.join(repo_path, fpath), "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                for m in re.finditer(r"(?:implementation|api|compileOnly|runtimeOnly)\s+project\s*\(\s*['\"]([^'\"]+)['\"]", text):
                    dep_name = m.group(1).replace(":", "/").split("/")[-1]
                    # Match by name to any module id ending with this name
                    for pid in id_by_path.values():
                        if pid.endswith("/" + dep_name) or pid == dep_name:
                            if pid != mod_id and pid not in deps:
                                deps.append(pid)
                                evidence.append({"from": mod_id, "to": pid,
                                                 "signal": f"gradle:project('{m.group(1)}')"})
            except Exception:
                pass

    # --- npm workspaces: scan package.json dependencies ---
    if build_system in ("npm-workspaces", "pnpm-workspace", "lerna"):
        pkg = os.path.join(repo_path, mod_path, "package.json") if mod_path != "." else os.path.join(repo_path, "package.json")
        if os.path.isfile(pkg):
            try:
                with open(pkg, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                # Build name -> id map
                name_to_id: dict[str, str] = {}
                for p, n in by_path.items():
                    pj = os.path.join(repo_path, p, "package.json") if p != "." else os.path.join(repo_path, "package.json")
                    if os.path.isfile(pj):
                        try:
                            with open(pj, "r", encoding="utf-8", errors="replace") as pf:
                                pd = json.load(pf)
                            nm = pd.get("name")
                            if nm:
                                name_to_id[nm] = id_by_path.get(p, p)
                        except Exception:
                            pass
                for dep_type in ("dependencies", "devDependencies", "peerDependencies"):
                    for dep_name in (data.get(dep_type) or {}):
                        if dep_name in name_to_id:
                            target_id = name_to_id[dep_name]
                            if target_id != mod_id and target_id not in deps:
                                deps.append(target_id)
                                evidence.append({"from": mod_id, "to": target_id,
                                                 "signal": f"npm:{dep_type}.{dep_name}"})
            except Exception:
                pass

    return {"depends_on": deps, "evidence": evidence}


def _determine_runtime_role(mod_path: str, node: dict, repo_path: str,
                            mod_files: list[str], build_system: str) -> dict:
    """Determine runtime_role, is_deployable, packaging, build_evidence."""
    role = "unknown"
    deployable = False
    packaging = None
    evidence: list[str] = []

    if build_system == "maven":
        pom = os.path.join(repo_path, mod_path, "pom.xml") if mod_path != "." else os.path.join(repo_path, "pom.xml")
        if os.path.isfile(pom):
            try:
                with open(pom, "r", encoding="utf-8", errors="replace") as f:
                    text = re.sub(r'\sxmlns="[^"]+"', "", f.read(), count=1)
                    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
                root = ET.fromstring(text)
                pkg = (root.findtext("packaging") or "jar").strip().lower()
                packaging = pkg
                # Check for spring-boot plugin
                plugins_el = root.find("build/plugins")
                has_spring_boot = False
                if plugins_el is not None:
                    for pl in plugins_el.findall("plugin"):
                        aid = (pl.findtext("artifactId") or "").strip()
                        if aid in ("spring-boot-maven-plugin", "quarkus-maven-plugin",
                                   "micronaut-maven-plugin"):
                            has_spring_boot = True
                            evidence.append(aid)
                # Check for mainClass in maven-jar-plugin
                has_main = False
                if plugins_el is not None:
                    for pl in plugins_el.findall("plugin"):
                        if (pl.findtext("artifactId") or "") == "maven-jar-plugin":
                            cfg = pl.find("configuration")
                            if cfg is not None and cfg.find("archive") is not None:
                                mf = cfg.find("configuration/archive/manifestFile") or cfg.find(".//mainClass")
                                if mf is not None and (mf.text or "").strip():
                                    has_main = True
                                    evidence.append(f"mainClass={mf.text.strip()}")

                if pkg == "pom":
                    role = "aggregator"
                    deployable = False
                elif pkg in ("jar", "war") and (has_spring_boot or has_main):
                    role = "service"
                    deployable = True
                elif pkg in ("jar", "war"):
                    role = "library"
                    deployable = False
                else:
                    role = "library"
            except Exception:
                pass

    elif build_system == "gradle":
        for fpath in mod_files:
            if not fpath.endswith((".gradle", ".gradle.kts")):
                continue
            try:
                with open(os.path.join(repo_path, fpath), "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                if "spring-boot" in text or "bootJar" in text or 'application {' in text:
                    role = "service"
                    deployable = True
                    packaging = "jar"
                    evidence.append("gradle:bootJar/application")
                    break
                elif "mainClass" in text:
                    role = "service"
                    deployable = True
                    packaging = "jar"
                    evidence.append("gradle:mainClass")
                    break
                else:
                    role = "library"
            except Exception:
                pass

    elif build_system in ("npm-workspaces", "pnpm-workspace", "lerna"):
        pkg = os.path.join(repo_path, mod_path, "package.json") if mod_path != "." else os.path.join(repo_path, "package.json")
        if os.path.isfile(pkg):
            try:
                with open(pkg, "r", encoding="utf-8", errors="replace") as f:
                    data = json.load(f)
                scripts = data.get("scripts") or {}
                has_bin = bool(data.get("bin"))
                if scripts.get("start"):
                    role = "service"
                    deployable = True
                    packaging = "node-app"
                    evidence.append("scripts.start")
                elif has_bin:
                    role = "cli"
                    deployable = True
                    packaging = "node-cli"
                    evidence.append("bin")
                else:
                    role = "library"
            except Exception:
                pass

    elif build_system in ("go-work",):
        # Check for func main() in Go files
        for fpath in mod_files:
            if fpath.endswith(".go"):
                try:
                    with open(os.path.join(repo_path, fpath), "r", encoding="utf-8", errors="replace") as f:
                        if "func main()" in f.read():
                            role = "service"
                            deployable = True
                            packaging = "go-binary"
                            evidence.append("func main()")
                            break
                except Exception:
                    pass
        else:
            role = "library"

    return {"runtime_role": role, "is_deployable": deployable,
            "packaging": packaging, "build_evidence": evidence}


def _count_source_and_test(mod_files: list[str]) -> dict:
    """Count source vs test files. Returns {source, test, is_placeholder}."""
    test_patterns = (
        re.compile(r"(^|/)test(/|$)", re.I),
        re.compile(r"(^|/)tests(/|$)", re.I),
        re.compile(r"(^|/)__tests__(/|$)", re.I),
        re.compile(r"(^|/)src/test(/|$)", re.I),
        re.compile(r"Test\.java$", re.I),
        re.compile(r"Tests\.java$", re.I),
        re.compile(r"_test\.go$", re.I),
        re.compile(r"\.test\.(ts|js|py)$", re.I),
        re.compile(r"\.spec\.(ts|js|py)$", re.I),
        re.compile(r"_spec\.rb$", re.I),
        re.compile(r"(^|/)spec(/|$)", re.I),
    )
    source = 0
    test = 0
    code_exts = (".py", ".java", ".kt", ".scala", ".ts", ".js", ".go", ".cs", ".rb",
                 ".rs", ".c", ".cpp", ".h", ".hpp")
    for fpath in mod_files:
        if not fpath.endswith(code_exts):
            continue
        is_test = any(p.search(fpath) for p in test_patterns)
        if is_test:
            test += 1
        else:
            source += 1
    is_placeholder = source == 0 and test == 0
    return {"source": source, "test": test, "is_placeholder": is_placeholder}


def _detect_entry_points(mod_path: str, repo_path: str,
                         mod_files: list[str], build_system: str) -> list[str]:
    """Detect startup entry points (Spring Boot app class, main, etc.)."""
    entry_points: list[str] = []

    # Java: @SpringBootApplication
    for fpath in mod_files:
        if not fpath.endswith((".java", ".kt")):
            continue
        try:
            with open(os.path.join(repo_path, fpath), "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            if re.search(r'@(?:org\.springframework\.boot\.autoconfigure\.)?SpringBootApplication', text):
                pkg = ""
                pm = re.search(r"^package\s+([\w.]+)\s*;", text, re.M)
                if pm:
                    pkg = pm.group(1) + "."
                cm = re.search(r"\b(?:class|interface)\s+(\w+)", text)
                if cm:
                    entry_points.append(pkg + cm.group(1))
        except Exception:
            pass

    # Node: package.json main / scripts.start
    pkg = os.path.join(repo_path, mod_path, "package.json") if mod_path != "." else os.path.join(repo_path, "package.json")
    if os.path.isfile(pkg):
        try:
            with open(pkg, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if data.get("main"):
                entry_points.append(data["main"])
            if (data.get("scripts") or {}).get("start"):
                start_script = data["scripts"]["start"]
                # Extract file path from "node src/server.js" patterns
                fm = re.search(r"(?:node|bun)\s+(\S+)", start_script)
                if fm:
                    entry_points.append(fm.group(1))
        except Exception:
            pass

    # Python: __main__.py
    for fpath in mod_files:
        if fpath.endswith("/__main__.py") or fpath == "__main__.py":
            entry_points.append(fpath)

    # Go: func main()
    for fpath in mod_files:
        if not fpath.endswith(".go"):
            continue
        try:
            with open(os.path.join(repo_path, fpath), "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            if re.search(r"^package\s+main\s*$", text, re.M) and "func main()" in text:
                entry_points.append(fpath)
        except Exception:
            pass

    # Rust: src/main.rs
    for fpath in mod_files:
        if fpath.endswith("src/main.rs"):
            entry_points.append(fpath)

    return entry_points


# --------------------------------------------------------------------------- #
# Tree assembly
# --------------------------------------------------------------------------- #
def _build_tree(build_system: str, nodes: list[dict], files: list[str], repo_path: str) -> dict:
    """Assemble the final module-tree dict from detector nodes + file list."""
    # Stable id per node: use the declared name chain rooted at the project.
    # Internal linking is done by `path` (unique). Root path is ".".
    project_name = os.path.basename(os.path.abspath(repo_path)) or "root"

    # Compute parent/children by path.
    by_path: dict[str, dict] = {}
    for n in nodes:
        # Last write wins so detectors can refine; but normally paths are unique.
        by_path[n["path"]] = n

    # Ensure every referenced parent_path exists; missing parents attach to root.
    for p, n in list(by_path.items()):
        pp = n.get("parent_path")
        if pp is None or pp == p:
            continue
        if pp not in by_path:
            # create an implied aggregate for the missing ancestor
            seg_name = os.path.basename(pp.rstrip("/")) or pp
            by_path[pp] = {"path": pp, "name": seg_name, "parent_path": None, "refined": False}

    # Build children index.
    children_by_path: dict[str, list[str]] = {p: [] for p in by_path}
    for p, n in by_path.items():
        pp = n.get("parent_path")
        if pp and pp != p and pp in children_by_path:
            children_by_path[pp].append(p)

    # Hierarchical ids: walk from root(s) downward.
    roots = [p for p, n in by_path.items() if not n.get("parent_path") or n["parent_path"] == p]
    if not roots:
        roots = list(by_path.keys())
    id_by_path: dict[str, str] = {}

    def _assign(path: str, parent_id: str | None):
        name = by_path[path]["name"] or os.path.basename(path.rstrip("/")) or "module"
        if parent_id is None:
            # Root node: use project name as the top id when path == "."
            node_id = project_name if path == "." else name
        else:
            node_id = f"{parent_id}/{name}" if path != "." else parent_id
        id_by_path[path] = node_id
        for child in sorted(children_by_path.get(path, [])):
            _assign(child, node_id)

    for r in sorted(roots):
        _assign(r, None)

    # File ownership: own files = under this dir prefix but not under any
    # descendant module dir. descendant module dirs = all nodes whose path
    # starts with "<path>/".
    def _prefix(path: str) -> str:
        return "" if path == "." else path + "/"

    descendant_prefixes = {}
    for p in by_path:
        pref = _prefix(p)
        desc = [_prefix(q) for q in by_path if q != p and q.startswith(pref)]
        descendant_prefixes[p] = desc

    def _own_files(p: str) -> int:
        pref = _prefix(p)
        desc = descendant_prefixes[p]
        count = 0
        for fpath in files:
            if not fpath.startswith(pref):
                continue
            if any(fpath.startswith(d) for d in desc):
                continue
            count += 1
        return count

    def _recursive_files(p: str) -> int:
        pref = _prefix(p)
        return sum(1 for fpath in files if fpath.startswith(pref))

    # Assemble modules list.
    modules: list[dict] = []
    leaf_count = 0
    for p in sorted(by_path.keys()):
        n = by_path[p]
        kids = sorted(children_by_path.get(p, []))
        is_aggregate = len(kids) > 0
        own = _own_files(p)
        rec = _recursive_files(p)
        if not is_aggregate:
            leaf_count += 1
        # Enrich: depends_on, runtime_role, is_deployable, is_placeholder,
        # entry_points, source/test counts, packaging, build_evidence.
        mod_files = [fp for fp in files if fp.startswith(_prefix(p))]
        dep_evidence = _compute_depends_on(p, n, by_path, id_by_path, repo_path, mod_files, build_system)
        role_info = _determine_runtime_role(p, n, repo_path, mod_files, build_system)
        counts = _count_source_and_test(mod_files)
        entry_pts = _detect_entry_points(p, repo_path, mod_files, build_system)

        modules.append({
            "id": id_by_path.get(p, p),
            "title": n["name"] or os.path.basename(p.rstrip("/")) or "module",
            "type": "aggregate" if is_aggregate else "leaf",
            "scope": [_prefix(p)] if p != "." else ["./"],
            "parent": (id_by_path.get(n["parent_path"]) if n.get("parent_path") and n["parent_path"] in id_by_path else None),
            "children": [id_by_path.get(c, c) for c in kids],
            "depends_on": dep_evidence.get("depends_on", []),
            "dep_evidence": dep_evidence.get("evidence", []),
            "runtime_role": role_info.get("runtime_role", "unknown"),
            "is_deployable": role_info.get("is_deployable", False),
            "is_placeholder": counts["is_placeholder"],
            "packaging": role_info.get("packaging"),
            "build_evidence": role_info.get("build_evidence", []),
            "entry_points": entry_pts,
            "source_file_count": counts["source"],
            "test_file_count": counts["test"],
            "own_file_count": own,
            "recursive_file_count": rec,
            "large": (not is_aggregate and rec > LARGE_LEAF_THRESHOLD),
            "refined": bool(n.get("refined", False)),
        })

    module_count = len(modules)
    # multi_module = more than one module AND at least one aggregate, i.e. a
    # real decomposition rather than a single top-level project.
    aggregates = sum(1 for m in modules if m["type"] == "aggregate")
    multi_module = module_count > 1 and aggregates >= 1

    # Order modules so parents come before children (stable, readable output).
    modules.sort(key=lambda m: (m["id"].count("/"), m["id"]))

    return {
        "multi_module": multi_module,
        "module_count": module_count,
        "leaf_count": leaf_count,
        "build_system": build_system,
        "project_name": project_name,
        "modules": modules,
    }


def _empty_result(repo_path: str) -> dict:
    return {
        "multi_module": False,
        "module_count": 0,
        "leaf_count": 0,
        "build_system": None,
        "project_name": os.path.basename(os.path.abspath(repo_path)) or "root",
        "modules": [],
    }


# --------------------------------------------------------------------------- #
# Text rendering (for injection into the structure prompt)
# --------------------------------------------------------------------------- #
def render_text(result: dict) -> str:
    """Render the module tree as a compact, readable text block."""
    if not result.get("multi_module"):
        bs = result.get("build_system")
        note = f"（检测到构建系统: {bs}，但未声明多模块）" if bs else "（未检测到多模块构建系统）"
        return f"非多模块项目{note}，建议使用全面模式或精简模式。"
    lines = [
        f"构建系统: {result['build_system']}",
        f"模块数: {result['module_count']}（其中叶子模块 {result['leaf_count']} 个）",
        "模块树：",
    ]
    by_id = {m["id"]: m for m in result["modules"]}
    # Build children lookup by id.
    children_by_id: dict[str, list[str]] = {m["id"]: [] for m in result["modules"]}
    roots = []
    for m in result["modules"]:
        pid = m.get("parent")
        if pid and pid in children_by_id:
            children_by_id[pid].append(m["id"])
        else:
            roots.append(m["id"])
    for m in result["modules"]:
        children_by_id[m["id"]].sort()

    def _emit(mid: str, depth: int):
        m = by_id[mid]
        indent = "  " * depth
        tag = "聚合" if m["type"] == "aggregate" else "叶子"
        scope = ",".join(m["scope"])
        # Build suffix with new enrichment fields
        suffix_parts: list[str] = []
        role = m.get("runtime_role", "unknown")
        if role != "unknown":
            suffix_parts.append(f"role={role}")
        if m.get("is_deployable"):
            suffix_parts.append("[deployable]")
        if m.get("is_placeholder"):
            suffix_parts.append("[placeholder]")
        deps = m.get("depends_on") or []
        if deps:
            suffix_parts.append(f"deps={','.join(deps)}")
        src = m.get("source_file_count", 0)
        tst = m.get("test_file_count", 0)
        if src or tst:
            suffix_parts.append(f"src/test={src}/{tst}")
        entry = m.get("entry_points") or []
        if entry:
            suffix_parts.append(f"entry={entry[0]}")
        suffix = (" " + " ".join(suffix_parts)) if suffix_parts else ""
        if m["type"] == "leaf":
            size = f"文件 {m['recursive_file_count']}"
            if m.get("large"):
                size += "（大模块，建议拆分多页）"
            lines.append(f"{indent}- {m['title']} [{tag}] scope={scope} {size}{suffix}")
        else:
            lines.append(f"{indent}- {m['title']} [{tag}] scope={scope} 自有文件 {m['own_file_count']}{suffix}")
        for c in children_by_id.get(mid, []):
            _emit(c, depth + 1)

    for r in sorted(roots):
        _emit(r, 0)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def scan_modules(repo_path: str, scan_path: str | None = None) -> dict:
    repo_path = os.path.abspath(repo_path)
    if not os.path.isdir(repo_path):
        print(f"Error: directory not found: {repo_path}", file=sys.stderr)
        sys.exit(1)

    files = _collect_files(repo_path, scan_path)

    detectors = (
        _detect_maven,
        _detect_gradle,
        _detect_cargo,
        _detect_go_work,
        _detect_npm_workspaces,
        _detect_pnpm,
        _detect_lerna,
        _detect_nx,
    )
    for det in detectors:
        try:
            found = det(repo_path)
        except Exception as e:  # a single detector must never abort the scan
            print(f"Warning: {det.__name__} failed: {e}", file=sys.stderr)
            found = None
        if found:
            build_system, nodes = found
            return _build_tree(build_system, nodes, files, repo_path)

    # Nothing detected: still report so the caller can decide on mode.
    res = _empty_result(repo_path)
    # Surface a build system hint if a lone build file exists (single-module).
    for fname, bs in (("pom.xml", "maven"), ("build.gradle", "gradle"),
                      ("Cargo.toml", "cargo"), ("package.json", "npm")):
        if os.path.isfile(os.path.join(repo_path, fname)):
            res["build_system"] = bs
            break
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a repo for multi-module structure boundaries")
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", default=None, help="Output file path (default: stdout)")
    parser.add_argument("--scan", "-s", default=None, help="Optional scan.json from scan_repo.py to reuse the file list")
    parser.add_argument("--format", default="json", choices=("json", "text"), help="Output format (default: json)")
    args = parser.parse_args()

    result = scan_modules(args.repo_path, args.scan)

    if args.format == "text":
        out = render_text(result)
    else:
        out = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out if args.format == "text" else json.dumps(result, ensure_ascii=False, indent=2))
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
