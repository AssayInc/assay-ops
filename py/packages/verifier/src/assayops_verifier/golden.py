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
from pydantic import ValidationError

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
        if not 1 <= length <= 64:
            raise ValueError("token length must be between 1 and 64")
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
        if task_id in self._builders:
            raise GoldenError(f"golden builder already registered for task_id={task_id!r}")
        self._builders[task_id] = builder

    def generate(self, task: TaskSpec, seed: str) -> GoldenTarget:
        """Regenerate the golden for ``task`` under ``seed`` (fail-closed on an unregistered task).

        ``seed`` is explicit (not read from ``task.seed``) so the verifier can regenerate either the
        canonical golden (``seed = task.seed``) or a fresh per-episode variant (re-seeding for
        anti-memorization, vector #14) without mutating the task spec.

        Failures fail closed: an unregistered task → ``UnknownTaskError``; an invalid golden (a bad
        resource value, an empty or duplicate-address set) → ``GoldenError``. A builder's own
        programming bug (e.g. a bad ``GoldenContext.token`` length) propagates unwrapped.
        """
        try:
            builder = self._builders[task.task_id]
        except KeyError:
            raise UnknownTaskError(task.task_id) from None
        try:
            resources = list(builder(GoldenContext(task=task, seed=seed)))
            return GoldenTarget(resources=tuple(resources))
        except ValidationError as exc:
            # A builder bug (bad resource, empty/ambiguous set) fails closed as a GoldenError — the
            # engine's single failure type — not a silent or partial golden (vector #15).
            raise GoldenError(f"invalid golden for task_id={task.task_id!r}: {exc}") from exc


def golden_digest(target: GoldenTarget) -> str:
    """The content address of a golden target: lowercase-hex SHA-256 over its RFC 8785 (JCS)
    canonical bytes — reusing the exact canonicalization the reward ledger signs (DECISIONS.md I3),
    not a re-roll. Byte-identical regeneration ⇒ identical address, so a grade is reproducible from
    (task, seed).

    Re-validates first: Pydantic ``frozen`` is shallow, so the account-B-internal golden could have
    been mutated after construction (its open ``properties`` dicts stay mutable). Re-validation
    makes the address pin a canonical, valid golden — a tampered one fails closed (``GoldenError``)
    instead of yielding a misleading address.
    """
    try:
        canonical = GoldenTarget.model_validate(target.model_dump())
    except ValidationError as exc:
        raise GoldenError(f"golden is not canonical (mutated after generation?): {exc}") from exc
    return canonical_digest(canonical).hex()
