"""The golden-target generator engine (DECISIONS.md 2A / T1 / §1 / §8).

``generate(task, seed)`` deterministically regenerates the expected normalized resource set the
account-B verifier grades deployed state against. It is **pure over (task, seed)**: it consumes the
task spec and a generation seed and *nothing else* — never the agent's ``synth``/``plan``/state,
never any agent-reachable channel (T1/§8; the verifier never runs agent code). The per-task "code"
is a ``GoldenBuilder``; real builders live in the private corpus (#76) and register here, keeping
this the **engine, not the corpus**.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from assayops_contracts import TaskSpec
from assayops_contracts.jcs import canonical_digest

from assayops_verifier.models import GoldenResource, GoldenTarget


class GoldenError(Exception):
    """A golden-generation failure — the engine fails closed, never an ambiguous golden."""


class UnknownTaskError(GoldenError):
    """No golden builder is registered for the task (fail-closed; never silently reward)."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"no golden builder registered for task_id={task_id!r}")
        self.task_id = task_id


@dataclass(frozen=True)
class GoldenContext:
    """The deterministic inputs a builder may read: the task spec and the generation seed."""

    task: TaskSpec
    seed: str

    def token(self, *parts: str, length: int = 12) -> str:
        """A deterministic ephemeral token derived from the seed (+ optional discriminators).

        No clock, no RNG — a SHA-256 over the seed and parts — so the same seed regenerates the
        same token byte-for-byte (what the content address rests on), while a fresh per-episode
        seed yields fresh identifiers (anti-memorization, vector #14).
        """
        material = "\x00".join((self.seed, *parts)).encode("utf-8")
        return hashlib.sha256(material).hexdigest()[:length]


# The per-task golden "code": given the deterministic context, emit the expected resources. A
# builder MUST be pure (no clock/RNG/network) — use ``GoldenContext.token`` for ephemeral ids.
GoldenBuilder = Callable[[GoldenContext], Iterable[GoldenResource]]


class GoldenRegistry:
    """Resolves a task to its golden builder — the seam between engine and (private) corpus."""

    def __init__(self) -> None:
        self._builders: dict[str, GoldenBuilder] = {}

    def register(self, task_id: str, builder: GoldenBuilder) -> None:
        self._builders[task_id] = builder

    def generate(self, task: TaskSpec, seed: str) -> GoldenTarget:
        """Regenerate the golden for ``task`` under ``seed`` (fail-closed on an unregistered task).

        ``seed`` is explicit (not read from ``task.seed``) so the verifier can regenerate either the
        canonical golden (``seed = task.seed``) or a fresh per-episode variant (re-seeding for
        anti-memorization, vector #14) without mutating the task spec.
        """
        try:
            builder = self._builders[task.task_id]
        except KeyError:
            raise UnknownTaskError(task.task_id) from None
        resources = list(builder(GoldenContext(task=task, seed=seed)))
        return _assemble(resources)


def _assemble(resources: list[GoldenResource]) -> GoldenTarget:
    """Normalize a builder's output into a golden target: reject ambiguity, fix canonical order."""
    addresses = [resource.address for resource in resources]
    duplicates = sorted({a for a in addresses if addresses.count(a) > 1})
    if duplicates:
        raise GoldenError(f"golden builder emitted duplicate addresses: {duplicates}")
    ordered = sorted(resources, key=lambda resource: resource.address)
    return GoldenTarget(resources=ordered)


def golden_digest(target: GoldenTarget) -> str:
    """The content address of a golden target: lowercase-hex SHA-256 over its RFC 8785 (JCS)
    canonical bytes — reusing the exact canonicalization the reward ledger signs (DECISIONS.md I3),
    not a re-roll. Byte-identical regeneration ⇒ identical address, so a grade is reproducible from
    (task, seed)."""
    return canonical_digest(target).hex()
