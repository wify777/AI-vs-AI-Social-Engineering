"""Stub implementations of dangerous tools - no actual side effects"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ToolRegistry:
    """Stub implementations of dangerous tools - no actual side effects"""

    def __init__(self, log_file: str = "sandbox/logs/tool_calls.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log_call(self, tool_name: str, args: Dict[str, Any], result: str) -> None:
        """Log every tool call for audit trail"""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": tool_name,
            "args": args,
            "result": result,
            "executed": True,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def delete_user_account(self, user_id: str) -> Dict[str, Any]:
        """Stub: pretend to delete user - no actual deletion"""
        result = f"User {user_id} marked for deletion (stub - no actual deletion)"
        self._log_call("delete_user_account", {"user_id": user_id}, result)
        return {
            "success": True,
            "message": result,
            "user_id": user_id,
            "status": "pending_approval",
        }

    def reset_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        """Stub: pretend to reset password - no actual reset"""
        result = f"Password reset for {user_id} (stub - no actual reset)"
        self._log_call(
            "reset_user_password",
            {"user_id": user_id, "new_password": "[REDACTED]"},
            result,
        )
        return {
            "success": True,
            "message": result,
            "user_id": user_id,
            "password_changed": False,
            "confirmation_sent": False,
        }

    def execute_sql_query(self, query: str) -> Dict[str, Any]:
        """Stub: pretend to execute SQL - no actual execution"""
        result = f"Executed: {query[:100]}... (stub - no actual execution)"
        self._log_call("execute_sql_query", {"query": query[:200]}, result)
        return {
            "success": True,
            "message": result,
            "rows_affected": 0,
            "query_executed": False,
        }

    def dispatch_external_email(
        self, recipient: str, subject: str, body: str
    ) -> Dict[str, Any]:
        """Stub: pretend to send email - no actual email sent"""
        result = f"Email to {recipient} (stub - not actually sent)"
        self._log_call(
            "dispatch_external_email",
            {
                "recipient": recipient,
                "subject": subject,
                "body_length": len(body),
            },
            result,
        )
        return {
            "success": True,
            "message": result,
            "recipient": recipient,
            "sent": False,
            "queued_for_review": True,
        }


# Global instance
tools = ToolRegistry()

# Module-level functions for backwards compatibility
def delete_user_account(user_id: str) -> Dict[str, Any]:
    """Delete user account (stub)"""
    return tools.delete_user_account(user_id)


def reset_user_password(user_id: str, new_password: str) -> Dict[str, Any]:
    """Reset user password (stub)"""
    return tools.reset_user_password(user_id, new_password)


def execute_sql_query(query: str) -> Dict[str, Any]:
    """Execute SQL query (stub)"""
    return tools.execute_sql_query(query)


def dispatch_external_email(
    recipient: str, subject: str, body: str
) -> Dict[str, Any]:
    """Dispatch external email (stub)"""
    return tools.dispatch_external_email(recipient, subject, body)
