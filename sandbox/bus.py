from schema.logger import log_turn

def run_conversation(parser_agent, admin_agent, initial_payload, max_turns, log_path, run_context):
    """
    runs a conversation between an admin and a parser until Admin calls a tool or max_turns is reached.

    Args:
        parser_agent: takes message history, returns Parser's next message
        admin_agent: takes message history, returns Admin's response(may include a tool call)
        initial_payload: the starting message/attack payload from Parser
        max_turns: int, safety cap on conversation length
        log_path: where to write logs (via logger.py)
        run_context: dict with run_id, config_hash, model_string, payload_id, condition, repetition, agent_role

    Returns:
        dict summarizing the outcome: {"outcome": "success"|"no_compliance", "turns_taken": int, "tool_called": str|None}
    """

    messages = [{"role": "user", "content": initial_payload}]

    for turn_number in range(1, max_turns + 1):
        # Admin responds to the conversation so far
        admin_response = admin_agent(messages)
        messages.append({"role": "assistant", "content": admin_response["text"]})

        # Log this turn regardless of outcome
        run_context["turn_number"] = turn_number
        run_context["agent_role"] = "admin"
        log_turn(
            log_path=log_path,
            messages=messages,
            tool_calls=admin_response.get("tool_calls", []),
            latency_ms=admin_response.get("latency_ms", 0),
            tokens_input=admin_response.get("tokens_input", 0),
            tokens_output=admin_response.get("tokens_output", 0),
            **{k: run_context[k] for k in [
                "run_id", "config_hash", "model_string", "payload_id",
                "condition", "repetition", "turn_number", "agent_role"
            ]},
        )

        # Stop condition: Admin called a tool
        if admin_response.get("tool_calls"):
            return {
                "outcome": "success",
                "turns_taken": turn_number,
                "tool_called": admin_response["tool_calls"][0]["tool_name"],
            }

        # Otherwise, Parser sends the next message
        parser_response = parser_agent(messages)
        messages.append({"role": "user", "content": parser_response["text"]})

        run_context["turn_number"] = turn_number
        run_context["agent_role"] = "parser"
        log_turn(
            log_path=log_path,
            messages=messages,
            tool_calls=[],
            latency_ms=parser_response.get("latency_ms", 0),
            tokens_input=parser_response.get("tokens_input", 0),
            tokens_output=parser_response.get("tokens_output", 0),
            **{k: run_context[k] for k in [
                "run_id", "config_hash", "model_string", "payload_id",
                "condition", "repetition", "turn_number", "agent_role"
            ]},
        )

    # Loop finished without a tool call
    return {"outcome": "no_compliance", "turns_taken": max_turns, "tool_called": None}