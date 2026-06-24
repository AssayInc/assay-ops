"""Cross-lane parity gate: the Python SECRET_KEYS must stay byte-for-byte in lockstep with the TS
@assayops/logger (ts/packages/logger/src/index.ts). The TS logger is KEPT, scoped to the TS
consumer/web surface; the two lanes share this redaction contract, so a drift in either fails here.
(Both lanes are checked out in the same CI tree, so this read resolves in the py lane.)"""

import re
from pathlib import Path

from assayops_logger import SECRET_KEYS

_TS_LOGGER = Path("ts/packages/logger/src/index.ts")


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / _TS_LOGGER).is_file():
            return parent
    raise AssertionError(f"could not locate the repo root containing {_TS_LOGGER}")


def _ts_source() -> str:
    return (_repo_root() / _TS_LOGGER).read_text(encoding="utf-8")


def _ts_secret_keys(source: str) -> tuple[str, ...]:
    match = re.search(r"const SECRET_KEYS = \[(.*?)\]", source, re.DOTALL)
    assert match, "SECRET_KEYS array not found in the TS logger"
    return tuple(re.findall(r'"([^"]+)"', match.group(1)))


def test_python_secret_keys_match_the_ts_lane() -> None:
    assert _ts_secret_keys(_ts_source()) == SECRET_KEYS


def test_ts_lane_also_redacts_the_header_keys() -> None:
    # x-api-key / set-cookie live in REDACT_KEYS (not SECRET_KEYS) — mirroring the TS header paths.
    source = _ts_source()
    assert '"x-api-key"' in source
    assert '"set-cookie"' in source
