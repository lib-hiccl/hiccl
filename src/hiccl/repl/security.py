"""hREPL Security & Audit Logging module."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime

logger = logging.getLogger("hiccl.repl.security")


def generate_token() -> str:
    """Generate a high-entropy 32-character authentication token."""
    return secrets.token_urlsafe(24)


def log_audit(code: str, success: bool, client_info: str = "Unknown") -> None:
    """Write evaluated code blocks and execution outcome to workspace audit log."""
    try:
        log_path = os.path.abspath(os.path.join(os.getcwd(), ".hrepl_audit.log"))
        timestamp = datetime.now().isoformat()
        status = "SUCCESS" if success else "ERROR"

        # Write code execution to audit log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                f"--- REPL COMMAND AT {timestamp} [{status}] (Client: {client_info}) ---\n"
            )
            f.write(code.rstrip())
            f.write(
                "\n-------------------------------------------------------------\n\n"
            )
    except Exception as e:
        logger.error(f"Failed to write to hREPL audit log: {e}")
