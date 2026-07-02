"""#176 leg 2: transcript -> OpenAI messages+tools, via inspect-ai's own converters.

The message conversion is inspect-ai's ``messages_to_openai`` (grounded, never hand-rolled -- a
hand-rolled ChatMessage->dict walk would drift from inspect's format on every release). The tools
come from the sample's model events (the schemas the model actually saw), converted from the public
``ToolInfo`` fields into the stable OpenAI tool shape.
"""

from __future__ import annotations

import asyncio

from conftest import as_dict
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.tool import ToolCall, ToolInfo, ToolParams

from assayops_trainer.messages import sample_to_openai_messages, sample_tools


def _model_event(*tools: ToolInfo) -> ModelEvent:
    return ModelEvent(
        model="hf/Qwen2.5-Coder-7B",
        input=[],
        tools=list(tools),
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
    )


def _sample_with_transcript() -> EvalSample:
    messages: list[ChatMessage] = [
        ChatMessageSystem(content="you fix terraform drift"),
        ChatMessageUser(content="re-enable bucket encryption"),
        ChatMessageAssistant(
            content="applying",
            tool_calls=[ToolCall(id="c1", function="bash", arguments={"cmd": "terraform apply"})],
        ),
        ChatMessageTool(content="Apply complete", tool_call_id="c1", function="bash"),
    ]
    bash_tool = ToolInfo(name="bash", description="run a shell command", parameters=ToolParams())
    editor = ToolInfo(name="text_editor", description="edit files", parameters=ToolParams())
    return EvalSample(
        id="drift-s3-encryption",
        epoch=1,
        input="re-enable bucket encryption",
        target="",
        messages=messages,
        # two model calls: the second re-advertises the same tool set -> dedup by name.
        events=[_model_event(bash_tool, editor), _model_event(bash_tool)],
    )


def test_messages_convert_to_the_openai_shape() -> None:
    out = asyncio.run(sample_to_openai_messages(_sample_with_transcript()))

    roles = [message["role"] for message in out]
    assert roles == ["system", "user", "assistant", "tool"]
    assistant = as_dict(out[2])
    assert assistant["tool_calls"][0]["function"]["name"] == "bash"
    assert out[3]["tool_call_id"] == "c1"


def test_tools_come_from_model_events_deduped_by_name() -> None:
    tools = sample_tools(_sample_with_transcript())

    names = [as_dict(tool)["function"]["name"] for tool in tools]
    assert names == ["bash", "text_editor"]  # deduped + name-sorted for a reproducible dataset
    bash = as_dict(tools[0])
    assert bash["type"] == "function"
    assert bash["function"]["description"] == "run a shell command"
    # the JSON-schema parameters survive (an object schema with no properties here)
    assert bash["function"]["parameters"]["type"] == "object"


def test_a_sample_without_model_events_has_no_tools() -> None:
    bare = EvalSample(
        id="t", epoch=1, input="x", target="", messages=[ChatMessageUser(content="x")]
    )

    assert sample_tools(bare) == []
