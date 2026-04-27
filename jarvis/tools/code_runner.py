"""
===========================================================
J.A.R.V.I.S. — Code Runner Tool
===========================================================
Sandboxed code execution with timeout and safety checks.
===========================================================
"""

import re
import logging
import subprocess
from jarvis.config import CODE_EXECUTION_TIMEOUT, BLOCKED_COMMANDS

logger = logging.getLogger("jarvis.tools.code_runner")


class CodeRunnerTool:
    """Execute code in a sandboxed subprocess."""

    def __init__(self, memory=None):
        self.memory = memory

    def execute(self, params: dict) -> str:
        code = params.get("code", "")
        language = params.get("language", "python").lower()
        if not code:
            return "No code provided, Sir."

        # Safety check
        violation = self._check_safety(code)
        if violation:
            return f"Code execution blocked for safety, Sir. Detected: {violation}"

        if language == "python":
            return self._run_python(code)
        elif language in ("bash", "shell", "cmd", "powershell", "ps1"):
            return self._run_shell(code, language)
        return f"Unsupported language: {language}, Sir."

    def _check_safety(self, code: str) -> str:
        """Check code for dangerous operations."""
        code_lower = code.lower()
        for blocked in BLOCKED_COMMANDS:
            if blocked.lower() in code_lower:
                return blocked
        return ""

    def _run_python(self, code: str) -> str:
        try:
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True, text=True,
                timeout=CODE_EXECUTION_TIMEOUT,
                cwd=None
            )
            output = result.stdout.strip()
            errors = result.stderr.strip()
            if result.returncode == 0:
                return f"Execution successful:\n{output}" if output else "Code executed successfully (no output)."
            else:
                return f"Code execution error:\n{errors}"
        except subprocess.TimeoutExpired:
            return f"Execution timed out after {CODE_EXECUTION_TIMEOUT}s, Sir."
        except Exception as e:
            return f"Execution failed: {e}"

    def _run_shell(self, code: str, language: str = "shell") -> str:
        try:
            if language in ("powershell", "ps1"):
                command = ["powershell", "-Command", code]
                shell_flag = False
            else:
                command = code
                shell_flag = True

            result = subprocess.run(
                command, shell=shell_flag,
                capture_output=True, text=True,
                timeout=CODE_EXECUTION_TIMEOUT
            )
            output = result.stdout.strip()
            errors = result.stderr.strip()
            if result.returncode == 0:
                return f"Command output:\n{output}" if output else "Command executed (no output)."
            else:
                return f"Command error:\n{errors}"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {CODE_EXECUTION_TIMEOUT}s, Sir."
        except Exception as e:
            return f"Command failed: {e}"
