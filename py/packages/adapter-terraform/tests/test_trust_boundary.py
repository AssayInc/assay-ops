"""The T1 moat at the adapter boundary: the grade is from deployed state ONLY.

Never the agent's ``terraform plan``/``show``, ``.tfstate``, or a provider plugin -- the adapter's
input domain excludes them by construction (DECISIONS.md T1 / §5 vectors #5 + #7 / §8).
"""

from __future__ import annotations

import inspect

from assayops_adapter_terraform import normalize


def test_normalize_consumes_only_reads_and_a_registry_no_plan_or_state_channel() -> None:
    # Structural proof: no plan / show / tfstate / provider parameter to sway the grade.
    parameters = set(inspect.signature(normalize).parameters)
    assert parameters == {"reads", "registry"}
