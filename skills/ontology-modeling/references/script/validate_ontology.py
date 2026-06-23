#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ontology Schema 校验器（自包含，无第三方依赖）。

用法：
    python validate_ontology.py [ontology_schema.json]
    默认路径 docs/ontology_schema.json

校验内容（覆盖 sdd-four-phase-analysis.md 问题13）：
  - 结构完整性：顶层字段、每个 object/edge/rule/sop 的必填字段
  - code 唯一性：objects / object 内 properties / edges / rules / sop_flows / sop_steps
  - edge 引用完整性：source_code / target_code 必须指向已定义的 object
  - 属性类型枚举：仅允许 String / Integer / Double
  - code 格式与长度：英文+下划线（允许数字，必须字母开头），≤32（rule ≤64）字符 —— 软告警

退出码：
    0 = 通过（可能有软告警）
    1 = 存在硬错误

如环境安装了 jsonschema，会额外按 ontology_schema.schema.json 做结构校验；
未安装也能运行——核心约束由本脚本内置检查保证。
"""

import json
import os
import re
import sys

OBJECT_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
RULE_CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
ALLOWED_PROP_TYPES = {"String", "Integer", "Double"}


def load_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    # 容忍 <artifact type="schema">...</artifact> 包裹（对话产物直接落盘时可能出现）
    if raw.startswith("<"):
        start = raw.find(">")
        end = raw.rfind("</")
        if start != -1 and end != -1 and end > start:
            raw = raw[start + 1:end].strip()
        # 去掉可能的 ```json 代码块包裹
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
    return json.loads(raw)


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def ok(self):
        return len(self.errors) == 0


def validate(data, rep):
    if not isinstance(data, dict):
        rep.err("顶层必须是 JSON 对象")
        return

    # 顶层字段
    if "domain" not in data or not str(data.get("domain", "")).strip():
        rep.warn("缺少 domain 或为空（业务领域归属）")
    if "objects" not in data:
        rep.err("缺少必填字段 objects（对象列表）")
        return
    objects = data.get("objects")
    if not isinstance(objects, list):
        rep.err("objects 必须是数组")
        return

    edges = data.get("edges", []) or []
    rules = data.get("rules", []) or []
    sop_flows = data.get("sop_flows", []) or []

    # ---- objects ----
    object_codes = set()
    for idx, obj in enumerate(objects):
        prefix = f"objects[{idx}]" + (f" ({obj.get('code')})" if isinstance(obj, dict) else "")
        if not isinstance(obj, dict):
            rep.err(f"{prefix}: 不是对象")
            continue
        for field in ("code", "name", "comment", "properties"):
            if field not in obj:
                rep.err(f"{prefix}: 缺少必填字段 {field}")
        code = obj.get("code")
        if not code:
            continue
        if code in object_codes:
            rep.err(f"{prefix}: 对象 code 重复 '{code}'")
        else:
            object_codes.add(code)
        if not OBJECT_CODE_RE.match(str(code)):
            rep.warn(f"{prefix}: code '{code}' 不符合格式（字母开头，仅英文字母/数字/下划线，≤32）")
        # properties
        props = obj.get("properties")
        if props is None:
            continue
        if not isinstance(props, list):
            rep.err(f"{prefix}: properties 必须是数组")
            continue
        prop_codes = set()
        for pidx, prop in enumerate(props):
            pprefix = f"{prefix}.properties[{pidx}]"
            if not isinstance(prop, dict):
                rep.err(f"{pprefix}: 不是对象")
                continue
            for field in ("code", "name", "comment", "type"):
                if field not in prop:
                    rep.err(f"{pprefix}: 缺少必填字段 {field}")
            pcode = prop.get("code")
            if pcode:
                if pcode in prop_codes:
                    rep.err(f"{pprefix}: 对象内属性 code 重复 '{pcode}'")
                else:
                    prop_codes.add(pcode)
                if not OBJECT_CODE_RE.match(str(pcode)):
                    rep.warn(f"{pprefix}: code '{pcode}' 不符合格式")
            ptype = prop.get("type")
            if ptype is not None and ptype not in ALLOWED_PROP_TYPES:
                rep.err(f"{pprefix}: type '{ptype}' 非法，仅允许 {sorted(ALLOWED_PROP_TYPES)}")

    # ---- edges ----
    edge_codes = set()
    for idx, edge in enumerate(edges):
        prefix = f"edges[{idx}]" + (f" ({edge.get('code')})" if isinstance(edge, dict) else "")
        if not isinstance(edge, dict):
            rep.err(f"{prefix}: 不是对象")
            continue
        for field in ("code", "name", "comment", "source_code", "target_code", "constraint"):
            if field not in edge:
                rep.err(f"{prefix}: 缺少必填字段 {field}")
        code = edge.get("code")
        if code:
            if code in edge_codes:
                rep.err(f"{prefix}: 关系 code 重复 '{code}'")
            else:
                edge_codes.add(code)
            if not OBJECT_CODE_RE.match(str(code)):
                rep.warn(f"{prefix}: code '{code}' 不符合格式")
        src = edge.get("source_code")
        tgt = edge.get("target_code")
        if src and src not in object_codes:
            rep.err(f"{prefix}: source_code '{src}' 未指向任何已定义对象（悬空引用）")
        if tgt and tgt not in object_codes:
            rep.err(f"{prefix}: target_code '{tgt}' 未指向任何已定义对象（悬空引用）")

    # ---- rules ----
    rule_codes = set()
    for idx, rule in enumerate(rules):
        prefix = f"rules[{idx}]" + (f" ({rule.get('code')})" if isinstance(rule, dict) else "")
        if not isinstance(rule, dict):
            rep.err(f"{prefix}: 不是对象")
            continue
        for field in ("code", "description"):
            if field not in rule:
                rep.err(f"{prefix}: 缺少必填字段 {field}")
        code = rule.get("code")
        if code:
            if code in rule_codes:
                rep.err(f"{prefix}: 规则 code 重复 '{code}'")
            else:
                rule_codes.add(code)
            if not RULE_CODE_RE.match(str(code)):
                rep.warn(f"{prefix}: code '{code}' 不符合格式（字母开头，≤64）")
        desc = str(rule.get("description", "")).strip()
        if not desc:
            rep.warn(f"{prefix}: description 为空")

    # ---- sop_flows ----
    flow_codes = set()
    for idx, flow in enumerate(sop_flows):
        prefix = f"sop_flows[{idx}]" + (f" ({flow.get('code')})" if isinstance(flow, dict) else "")
        if not isinstance(flow, dict):
            rep.err(f"{prefix}: 不是对象")
            continue
        for field in ("code", "title", "steps"):
            if field not in flow:
                rep.err(f"{prefix}: 缺少必填字段 {field}")
        code = flow.get("code")
        if code:
            if code in flow_codes:
                rep.err(f"{prefix}: SOP code 重复 '{code}'")
            else:
                flow_codes.add(code)
            if not OBJECT_CODE_RE.match(str(code)):
                rep.warn(f"{prefix}: code '{code}' 不符合格式")
        steps = flow.get("steps")
        if steps is None:
            continue
        if not isinstance(steps, list):
            rep.err(f"{prefix}: steps 必须是数组")
            continue
        step_codes = set()
        for sidx, step in enumerate(steps):
            sprefix = f"{prefix}.steps[{sidx}]"
            if not isinstance(step, dict):
                rep.err(f"{sprefix}: 不是对象")
                continue
            for field in ("code", "title"):
                if field not in step:
                    rep.err(f"{sprefix}: 缺少必填字段 {field}")
            scode = step.get("code")
            if scode:
                if scode in step_codes:
                    rep.err(f"{sprefix}: 流程内步骤 code 重复 '{scode}'")
                else:
                    step_codes.add(scode)
                if not OBJECT_CODE_RE.match(str(scode)):
                    rep.warn(f"{sprefix}: code '{scode}' 不符合格式")

    # 统计
    step_count = sum(
        len(f.get("steps") or []) for f in sop_flows if isinstance(f, dict)
    )
    rep._stats = {
        "objects": len(objects),
        "edges": len(edges),
        "rules": len(rules),
        "sop_flows": len(sop_flows),
        "sop_steps": step_count,
    }


def try_jsonschema(path, rep):
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "ontology_schema.schema.json"
    )
    try:
        import jsonschema  # type: ignore
    except Exception:
        return  # 未安装 jsonschema，跳过（核心约束已由内置检查覆盖）
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validator = jsonschema.Draft7Validator(schema)
        extra = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        for e in extra:
            loc = "/".join(str(p) for p in e.path) or "<root>"
            rep.warn(f"[jsonschema] {loc}: {e.message}")
    except Exception as e:  # pragma: no cover
        rep.warn(f"jsonschema 附加校验未能运行: {e}")


def main(argv):
    path = argv[1] if len(argv) > 1 else "docs/ontology_schema.json"
    if not os.path.exists(path):
        print(f"错误: 文件不存在: {path}", file=sys.stderr)
        return 2
    try:
        data = load_schema(path)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}", file=sys.stderr)
        return 1

    rep = Reporter()
    validate(data, rep)
    try_jsonschema(path, rep)
    stats = getattr(rep, "_stats", {})

    print("=== Ontology Schema 校验报告 ===")
    if stats:
        print(
            "统计: objects={objects}, edges={edges}, rules={rules}, "
            "sop_flows={sop_flows}, sop_steps={sop_steps}".format(**stats)
        )
    for w in rep.warnings:
        print(f"  ⚠ WARN  {w}")
    for e in rep.errors:
        print(f"  ✗ ERROR {e}")

    if rep.ok():
        print(f"结果: 通过（{len(rep.warnings)} 条软告警）")
        return 0
    else:
        print(f"结果: 失败（{len(rep.errors)} 条错误, {len(rep.warnings)} 条软告警）")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
