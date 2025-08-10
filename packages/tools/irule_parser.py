"""iRule parser minimal implementation.
Parses events and commands with line numbers; detects unsupported constructs.
"""
from typing import Dict, Any, List
import re

SUPPORTED_EVENTS = {"CLIENT_ACCEPTED", "HTTP_REQUEST", "HTTP_RESPONSE"}
SUPPORTED_COMMANDS = {"when","if","elseif","else","switch","set","return","HTTP::uri","HTTP::method","HTTP::path","HTTP::query","HTTP::header","regexp","string","class"}
PARTIAL_OR_UNSUPPORTED = {"table","after","HSL::send","binary","iControl","sideband"}

EVENT_RE = re.compile(r'^\s*when\s+(\w+)\s*\{?')
CMD_RE = re.compile(r'^(?P<indent>\s*)(?P<cmd>[A-Za-z0-9_:]+)')


def parse_irule(code: str) -> Dict[str, Any]:
    lines = code.splitlines()
    events: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    current_event = None
    for idx, raw in enumerate(lines, start=1):
        m = EVENT_RE.match(raw)
        if m:
            evt = m.group(1)
            ev_obj = {"type": "event", "name": evt, "line": idx, "body": []}
            events.append(ev_obj)
            current_event = ev_obj
            if evt not in SUPPORTED_EVENTS:
                diagnostics.append({"severity": "warning", "line": idx, "message": f"Unsupported event {evt}"})
            continue
        if not raw.strip():
            continue
        # command extraction inside event
        if current_event:
            cmd_match = CMD_RE.match(raw)
            if cmd_match:
                cmd = cmd_match.group('cmd')
                node = {"type": "command", "cmd": cmd, "line": idx, "raw": raw.strip()}
                current_event["body"].append(node)
                if not any(cmd.startswith(sc) for sc in SUPPORTED_COMMANDS):
                    severity = "info"
                    for uns in PARTIAL_OR_UNSUPPORTED:
                        if cmd.startswith(uns):
                            severity = "error"
                            diagnostics.append({"severity": severity, "line": idx, "message": f"Unsupported construct {cmd}"})
                            break
            else:
                continue
    ast = {"type": "root", "events": events, "lines": len(lines)}
    return {"ast": ast, "diagnostics": diagnostics}
