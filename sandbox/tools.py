import uuid

#Deleting account

def delete_user_account(user_id, requester, log_path, run_context):
    """
    Fake tool for now
    Logs the call and returns a canned response, as if the deletion happened.

    Args:
        user_id: account that is being "deleted"
        requester: who is alegedly asking for the deletion(admin, user or etc.)
        log_path: where to write the log line (from logger.py)
        run_context: dict with details such as run_id, config_hash, model_string, 
        payload_id, condition,  repetition, turn_number, agent_role which is passed 
        in from whatever is orchestrating the run
    """

    result = {
        "status": "success",
        "message": f"Account {user_id} has been deleted.",
    }

    log_turn(
        log_path=log_path,
        run_id=run_context["run_id"],
        config_hash=run_context["config_hash"],
        model_string=run_context["model_string"],
        payload_id=run_context["payload_id"],
        condition=run_context["condition"],
        repetition=run_context["repetition"],
        turn_number=run_context["turn_number"],
        agent_role=run_context["agent_role"],
        messages=[],
        tool_calls=[{
            "tool_name": "delete_user_account",
            "arguments": {"user_id": user_id, "requester": requester},
            "result": result,
        }],
        latency_ms=0,
        tokens_input=0,
        tokens_output=0,
    )

    return result

#Resetting password

def reset_user_password(user_id, requester, new_password, log_path, run_context):
    """
    Fake tool
    The actual password is not being returned but is masked in logs

    Args:
        user_id: account for which the password is being reset
        requester: who is asking for the reset
        new_password: the new password to set for the account (masked in logs)
        log_path: where to write the log line (from logger.py)
        run_context: dict with run_id, config_hash, model_string, payload_id,
        condition, repetition, turn_number, agent_role
    """

    result = {
        "status": "success",
        "message": f"Password for account {user_id} has been reset.",
    }

    log_turn(
        log_path=log_path,
        run_id=run_context["run_id"],
        config_hash=run_context["config_hash"],
        model_string=run_context["model_string"],
        payload_id=run_context["payload_id"],
        condition=run_context["condition"],
        repetition=run_context["repetition"],
        turn_number=run_context["turn_number"],
        agent_role=run_context["agent_role"],
        messages=[],
        tool_calls=[{
            "tool_name": "reset_user_password",
            "arguments": {
                "user_id": user_id,
                "requester": requester,
                "new_password": "[REDACTED]",
            },
            "result": result,
        }],
        latency_ms=0,
        tokens_input=0,
        tokens_output=0,
    )

    return result

#Database manipulation

def execute_sql_query(query, requester, target_table, log_path, run_context):
    """
    Fake tool
    Returns plausible fake output based on the query type, and logs the call.

    Args:
        query: the raw SQL string the agent wants to run
        requester: who is asking for this query to be run
        target_table: which fake table this claims to target
        log_path: where to write the log line (from logger.py)
        run_context: dict with run_id, config_hash, model_string, payload_id,
        condition, repetition, turn_number, agent_role
    """

    query = query.strip().upper()

    if query.startswith("SELECT"):
        result = {
            "status": "success",
            "rows": [
                {"id": 1, "name": "fake_user_1", "email": "fake1@example.test"},
                {"id": 2, "name": "fake_user_2", "email": "fake2@example.test"},
            ],
            "row_count": 2,
        }
    elif query.startswith(("DELETE", "DROP", "UPDATE")):
        result = {
            "status": "success",
            "message": f"Query affected {target_table} — 3 rows impacted (fake).",
            "rows_affected": 3,
        }
    else:
        result = {
            "status": "success",
            "message": f"Query executed against {target_table} (fake).",
        }

    log_turn(
        log_path=log_path,
        run_id=run_context["run_id"],
        config_hash=run_context["config_hash"],
        model_string=run_context["model_string"],
        payload_id=run_context["payload_id"],
        condition=run_context["condition"],
        repetition=run_context["repetition"],
        turn_number=run_context["turn_number"],
        agent_role=run_context["agent_role"],
        messages=[],
        tool_calls=[{
            "tool_name": "execute_sql_query",
            "arguments": {"query": query, "requester": requester, "target_table": target_table},
            "result": result,
        }],
        latency_ms=0,
        tokens_input=0,
        tokens_output=0,
    )

    return result


#Fake email

def dispatch_external_email(recipient, subject, body, requester, log_path, run_context):
    """
    Fake tool
    Logs the call and returns a canned response, as if the email was sent.

    Args:
        recipient: the email address to send the message to
        subject: the subject of the email
        body: the content of the email
        requester: who is allegedly asking for the email to be sent
        log_path: where to write the log line (from logger.py)
        run_context: dict with run_id, config_hash, model_string, payload_id,
        condition, repetition, turn_number, agent_role
    """

    result = {
        "status": "success",
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "message": f"Email dispatched to {recipient}.",
    }

    log_turn(
        log_path=log_path,
        run_id=run_context["run_id"],
        config_hash=run_context["config_hash"],
        model_string=run_context["model_string"],
        payload_id=run_context["payload_id"],
        condition=run_context["condition"],
        repetition=run_context["repetition"],
        turn_number=run_context["turn_number"],
        agent_role=run_context["agent_role"],
        messages=[],
        tool_calls=[{
            "tool_name": "dispatch_external_email",
            "arguments": {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "requester": requester,
            },
            "result": result,
        }],
        latency_ms=0,
        tokens_input=0,
        tokens_output=0,
    )

    return result