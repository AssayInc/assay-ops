"""Transcript -> OpenAI messages+tools, grounded in inspect-ai's own converters.

Messages go through inspect-ai's ``messages_to_openai`` -- never a hand-rolled ``ChatMessage``->dict
walk, which would drift from inspect's format (tool-call encoding, content parts) on every release.
One repair on top: the wire shape carries tool-call ``arguments`` as a JSON STRING, but TRL's
conversational path renders ``tool_call.arguments | tojson`` verbatim -- a wire string would
double-encode into every training target, so arguments are parsed back to dicts (TRL's documented
conversational format; fail closed on anything unparseable). Tools come from the sample's model
events -- the schemas the model saw -- converted from the public ``ToolInfo`` fields into the
stable OpenAI tool shape and deduped by name so the emitted dataset is reproducible.
"""

from __future__ import annotations

import json

from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample
from inspect_ai.model import messages_to_openai
from inspect_ai.tool import ToolInfo

from assayops_trainer.records import JsonObject


async def sample_to_openai_messages(sample: EvalSample) -> list[JsonObject]:
    """The sample's full transcript as OpenAI message dicts (copied to plain dicts)."""
    converted = await messages_to_openai(sample.messages)
    # messages_to_openai returns typed dicts; copy each to a plain JSON object for the record.
    return [_with_dict_tool_call_arguments(dict(message)) for message in converted]


def _with_dict_tool_call_arguments(message: JsonObject) -> JsonObject:
    """Rewrite wire-format tool-call ``arguments`` (JSON strings) to dicts, fail closed.

    inspect's own wire strings always parse (they are ``json.dumps`` of a dict); an unparseable or
    non-object value can only come from a foreign/hand-edited log -- never emit a training record
    whose tool-call syntax we cannot faithfully reconstruct.
    """
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return message
    message["tool_calls"] = [_with_dict_arguments(call) for call in tool_calls]
    return message


def _with_dict_arguments(call: object) -> JsonObject:
    if not isinstance(call, dict):
        raise ValueError(f"tool call is not an object: {call!r}")
    function = call.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"tool call has no function object: {call!r}")
    arguments = function.get("arguments")
    if isinstance(arguments, dict):
        return {**call, "function": {**function, "arguments": arguments}}
    if not isinstance(arguments, str):
        raise ValueError(
            f"tool-call arguments are neither a dict nor a wire JSON string: {arguments!r}"
        )
    try:
        parsed: object = json.loads(arguments)
    except json.JSONDecodeError as error:
        raise ValueError(f"tool-call arguments are not valid JSON: {arguments!r}") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"tool-call arguments are not a JSON object: {arguments!r}")
    return {**call, "function": {**function, "arguments": parsed}}


def sample_tools(sample: EvalSample) -> list[JsonObject]:
    """The union of tool schemas the model saw across the sample's model events (deduped, sorted).

    Empty when the log carries no model events (events disabled, or a sample that never called the
    model) -- the record then trains on messages alone. When a tool name recurs across events the
    FIRST advertised schema wins (a react episode advertises a stable set, so this is a no-op in
    practice).
    """
    by_name: dict[str, ToolInfo] = {}
    for event in sample.events or []:
        if isinstance(event, ModelEvent):
            for tool in event.tools:
                by_name.setdefault(tool.name, tool)
    return [_tool_info_to_openai(by_name[name]) for name in sorted(by_name)]


def _tool_info_to_openai(tool: ToolInfo) -> JsonObject:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            # exclude_none matches inspect's own OpenAI tool mapping -- drop null JSON-schema fields
            # rather than emit `"description": null` etc. into the parameters spec.
            "parameters": tool.parameters.model_dump(mode="json", exclude_none=True),
        },
    }
