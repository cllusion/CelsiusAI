"""
Code Engine - Security Analysis, Code Generation, and Command Management
Celsius AI - Static Analysis and Code Intelligence Module
"""

import ast
import re
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

SECURITY_PATTERNS = {
    "hardcoded_secret": [
        r'(?i)(password|passwd|pwd|secret|api_key|apikey|token|auth)\s*=\s*["\'][^"\']{4,}["\']',
    ],
    "sql_injection": [
        r'execute\s*\(\s*["\'].*%s.*["\']',
        r'f["\'].*SELECT.*\{.*\}',
    ],
    "command_injection": [
        r'os\.system\s*\(\s*(?:f["\']|["\'].*\+)',
        r'subprocess\.(?:run|call|Popen)\s*\(.*shell=True',
        r'eval\s*\(\s*(?:input|request)',
    ],
    "path_traversal": [
        r'open\s*\(\s*(?:f["\']|["\'].*\+)',
    ],
    "xss": [
        r'innerHTML\s*=\s*(?:user|input|request|query)',
    ],
    "insecure_deserialization": [
        r'pickle\.loads\s*\(',
        r'yaml\.load\s*\(\s*(?!.*Loader)',
    ],
}

SEVERITY_MAP = {
    "hardcoded_secret": "high",
    "sql_injection": "critical",
    "command_injection": "critical",
    "path_traversal": "medium",
    "xss": "medium",
    "insecure_deserialization": "high",
}

LANGUAGE_TEMPLATES = {
    "python": {
        "http_server": '''from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", {port}), Handler)
    print(f"Serving on port {port}")
    server.serve_forever()
''',
        "class": '''class {name}:
    """A {name} class."""

    def __init__(self{init_args}):
        pass

    def __repr__(self) -> str:
        return f"{name}()"
''',
        "async_task": '''import asyncio

async def {name}({args}) -> None:
    """Async task: {name}."""
    try:
        # TODO: implement task logic
        await asyncio.sleep(0)
    except Exception as e:
        print(f"Task {name} failed: {{e}}")
        raise

if __name__ == "__main__":
    asyncio.run({name}())
''',
    },
    "typescript": {
        "api_route": '''import {{ NextRequest, NextResponse }} from "next/server";

export async function GET(req: NextRequest) {{
  try {{
    return NextResponse.json({{ status: "ok" }});
  }} catch (error) {{
    return NextResponse.json({{ error: "Internal Server Error" }}, {{ status: 500 }});
  }}
}}

export async function POST(req: NextRequest) {{
  const body = await req.json();
  return NextResponse.json({{ received: body }});
}}
''',
        "component": '''import React, {{ useState }} from "react";

interface {name}Props {{
  // define props
}}

export const {name}: React.FC<{name}Props> = () => {{
  const [state, setState] = useState(null);

  return (
    <div className="{name_lower}">
      <h1>{name}</h1>
    </div>
  );
}};

export default {name};
''',
    },
}


class CodeEngine:
    """Engine for code security analysis, generation, and command management."""

    def __init__(self):
        self.pending_commands: List[Dict[str, Any]] = []
        self.command_history: List[Dict[str, Any]] = []
        self._cmd_counter: int = 0

    def analyze_security(self, code: str, filename: str = "<string>") -> Dict[str, Any]:
        """Scan code text for security vulnerabilities using regex patterns."""
        findings = []
        lines = code.splitlines()

        for vuln_type, patterns in SECURITY_PATTERNS.items():
            for pattern in patterns:
                for lineno, line in enumerate(lines, start=1):
                    if re.search(pattern, line):
                        findings.append({
                            "type": vuln_type,
                            "line": lineno,
                            "content": line.strip(),
                            "severity": SEVERITY_MAP.get(vuln_type, "medium"),
                        })

        critical = sum(1 for f in findings if f["severity"] == "critical")
        high = sum(1 for f in findings if f["severity"] == "high")

        if critical > 0:
            risk_level = "critical"
        elif high > 0:
            risk_level = "high"
        elif findings:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "filename": filename,
            "findings": findings,
            "total_issues": len(findings),
            "risk_level": risk_level,
            "scanned_lines": len(lines),
        }

    def analyze_file(self, path: str) -> Dict[str, Any]:
        """Read a file from disk and run security analysis."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except OSError as e:
            return {"error": str(e), "path": path}

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "unknown"
        result = self.analyze_security(code, filename=path)
        result["path"] = path
        result["language"] = ext
        return result

    def analyze_python_syntax(self, code: str) -> Dict[str, Any]:
        """Use ast.parse() to check Python code for syntax errors."""
        try:
            tree = ast.parse(code)
            return {
                "valid": True,
                "error": None,
                "node_count": len(list(ast.walk(tree))),
            }
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
            }

    def generate_snippet(self, language: str, template: str, **kwargs) -> str:
        """Return a code snippet from LANGUAGE_TEMPLATES."""
        lang_templates = LANGUAGE_TEMPLATES.get(language.lower())
        if not lang_templates:
            available = list(LANGUAGE_TEMPLATES.keys())
            return f"# Language '{language}' not supported. Available: {available}"

        tmpl = lang_templates.get(template)
        if not tmpl:
            available = list(lang_templates.keys())
            return f"# Template '{template}' not found for {language}. Available: {available}"

        try:
            return tmpl.format(**kwargs)
        except KeyError as e:
            return f"# Missing template variable: {e}"

    def queue_command(self, cmd: str, reason: str) -> str:
        """Add a command to the pending queue and return an approval message."""
        self._cmd_counter += 1
        cmd_id = self._cmd_counter
        self.pending_commands.append({
            "id": cmd_id,
            "cmd": cmd,
            "reason": reason,
            "queued_at": datetime.now().isoformat(),
            "status": "pending",
        })
        return (
            f"Command queued with ID {cmd_id}.\n"
            f"Command: {cmd}\n"
            f"Reason: {reason}\n"
            f"Use approve_command({cmd_id}) to execute."
        )

    def approve_command(self, cmd_id: int) -> Dict[str, Any]:
        """Execute a queued command by its ID."""
        entry = next((c for c in self.pending_commands if c["id"] == cmd_id), None)
        if not entry:
            return {"error": f"No pending command with ID {cmd_id}"}

        self.pending_commands.remove(entry)
        entry["status"] = "running"
        entry["started_at"] = datetime.now().isoformat()

        try:
            result = subprocess.run(
                entry["cmd"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            entry.update({
                "status": "completed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "completed_at": datetime.now().isoformat(),
            })
        except subprocess.TimeoutExpired:
            entry.update({"status": "timeout", "error": "Command timed out after 30s"})
        except Exception as e:
            entry.update({"status": "error", "error": str(e)})

        self.command_history.append(entry)
        return entry

    def list_pending(self) -> List[Dict[str, Any]]:
        """Return all pending commands."""
        return list(self.pending_commands)

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the last 20 executed commands."""
        return self.command_history[-20:]
