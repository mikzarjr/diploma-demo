import re
from typing import Any


def run_rule_based_check(
        rule_config: dict[str, Any],
        transcript: str,
        turns: list[dict],
        output_type: str,
) -> dict:
    rule_type = rule_config.get("rule_type") or rule_config.get("type", "contains")
    value = rule_config.get("value", "")
    speaker_filter = rule_config.get("speaker")
    turns_limit = rule_config.get("turns_limit")

    result = {
        "value_boolean": None,
        "value_score": None,
        "value_category": None,
        "raw_response": None,
    }

    filtered_turns = turns
    if speaker_filter:
        filtered_turns = [t for t in turns if t.get("speaker") == speaker_filter]

    if turns_limit:
        filtered_turns = filtered_turns[:turns_limit]

    filtered_text = " ".join(t.get("text", "") for t in filtered_turns).lower()

    if rule_type == "contains":
        found = value.lower() in (filtered_text if filtered_turns else transcript.lower())
        result["value_boolean"] = found
        result["raw_response"] = f"contains '{value}': {found}"

    elif rule_type == "regex":
        pattern = rule_config.get("pattern", value)
        text_to_search = filtered_text if filtered_turns else transcript.lower()
        found = bool(re.search(pattern, text_to_search, re.IGNORECASE))
        result["value_boolean"] = found
        result["raw_response"] = f"regex '{pattern}': {found}"

    elif rule_type == "starts_with":
        if filtered_turns:
            first_text = filtered_turns[0].get("text", "").lower()
            found = first_text.startswith(value.lower())
        else:
            found = transcript.lower().startswith(value.lower())
        result["value_boolean"] = found
        result["raw_response"] = f"starts_with '{value}': {found}"

    elif rule_type == "min_turns":
        count = len(filtered_turns)
        passed = count >= int(value)
        result["value_boolean"] = passed
        result["raw_response"] = f"min_turns {value}: actual={count}, passed={passed}"

    else:
        result["value_boolean"] = False
        result["raw_response"] = f"Unknown rule type: {rule_type}"

    if output_type == "score" and result["value_boolean"] is not None:
        result["value_score"] = 100.0 if result["value_boolean"] else 0.0
    elif output_type == "category" and result["value_boolean"] is not None:
        result["value_category"] = "passed" if result["value_boolean"] else "failed"

    return result
