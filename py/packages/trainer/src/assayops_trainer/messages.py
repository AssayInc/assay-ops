"""Transcript -> OpenAI messages+tools, grounded in inspect-ai's own converters.

Messages go through inspect-ai's ``messages_to_openai`` -- never a hand-rolled ``ChatMessage``->dict
walk, which would drift from inspect's format (tool-call encoding, content parts) on every release.
Tools come from the sample's model events -- the schemas the model saw -- converted from the
public ``ToolInfo`` fields into the stable OpenAI tool shape and deduped by name so the emitted
dataset is reproducible.
"""

from __future__ import annotations

from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample
from inspect_ai.model import messages_to_openai
from inspect_ai.tool import ToolInfo

from assayops_trainer.records import JsonObject


async def sample_to_openai_messages(sample: EvalSample) -> list[JsonObject]:
    """The sample's full transcript as OpenAI message dicts (copied to plain dicts)."""
    converted = await messages_to_openai(sample.messages)
    # messages_to_openai returns typed dicts; copy each to a plain JSON object for the record.
    return [dict(message) for message in converted]


def sample_tools(sample: EvalSample) -> list[JsonObject]:
    """The union of tool schemas the model saw across the sample's model events (deduped, sorted).

    Empty when the log carries no model events (events disabled, or a sample that never called the
    model) -- the record then trains on messages alone.
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
            "parameters": tool.parameters.model_dump(mode="json"),
        },
    }
