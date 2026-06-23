"""Test helpers: parse the captured JSON log output (one event per line) into dicts."""

import io
import json


def parse_log_lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
