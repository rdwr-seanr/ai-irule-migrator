"""AppShape++ generator.
Converts AST + plan to code with inline line refs.
"""
from typing import Dict, Any, List

MAPPINGS = {
    'HTTP::header': 'set_header',
    'HTTP::uri': 'rewrite_uri',
}

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
            for k, v in MAPPINGS.items():
                if cmd.startswith(k):
                    target = v
                    break
            if target:
                out_lines.append(f"{target}  # line {line} : {cmd}")
                mapping.append({"source_cmd": cmd, "line": line, "target": target})
            else:
                out_lines.append(f"# unmapped line {line}: {cmd}")
                mapping.append({"source_cmd": cmd, "line": line, "target": None})
    code = "\n".join(out_lines) + "\n"
    return {"code": code, "mapping": mapping}
