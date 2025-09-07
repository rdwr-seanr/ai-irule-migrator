"""AppShape++ generator.
Converts AST + plan to code with inline line refs.
Only emits targets that exist in the curated mapping dataset.
"""
from typing import Dict, Any, List
import json
from pathlib import Path

# Load curated mapping file if present (admin-extensible)
_DEFAULT = {
    'HTTP::header': {'target': 'set_header', 'source': 'docs/AlteonOS-34-5-4-AppShape-Ref.pdf'},
    'HTTP::uri': {'target': 'rewrite_uri', 'source': 'docs/AlteonOS-34-5-4-AppShape-Ref.pdf'},
}

def _load_mappings():
    try:
        p = Path(__file__).parent / 'capability_map.json'
        if p.exists():
            with p.open('r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception:
        pass
    return _DEFAULT

MAPPINGS = _load_mappings()

def generate_appshape(ast: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = ast.get('events', [])
    out_lines: List[str] = ["# Generated AppShape++ script"]
    mapping: List[Dict[str, Any]] = []
    for ev in events:
        out_lines.append(f"# Event: {ev['name']} (line {ev['line']})")
        for node in ev.get('body', []):
            cmd = node['cmd']
            line = node['line']
            target = None
            source = None
            for k, meta in MAPPINGS.items():
                if cmd.startswith(k):
                    target = meta.get('target') if isinstance(meta, dict) else meta
                    source = meta.get('source') if isinstance(meta, dict) else None
                    break
            if target:
                out_lines.append(f"{target}  # line {line} : {cmd}")
                mapping.append({"source_cmd": cmd, "line": line, "target": target, "source": source})
            else:
                out_lines.append(f"# unmapped line {line}: {cmd}")
                mapping.append({"source_cmd": cmd, "line": line, "target": None})
    code = "\n".join(out_lines) + "\n"
    return {"code": code, "mapping": mapping}
