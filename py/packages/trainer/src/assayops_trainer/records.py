"""The SFT record shapes -- one rejection-sampled training example + its provenance.

``SFTExample`` carries the two things a positive trajectory yields: the conversational transcript
(``messages`` + ``tools``, the OpenAI format TRL trains on) and its ``Provenance`` (what makes the
set auditable + reproducible from a manifest -- #78). ``training_record()`` emits ONLY the trained
columns; provenance lands in the manifest, never in the trained data.

Both models are hardened (``frozen`` + ``extra="forbid"`` -- pydantic-v2 skill): a stray key or a
post-hoc mutation is a bug in the ETL, not something to silently absorb into a training record.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# An open JSON object (a message / tool-schema dict). `object` is Python's `unknown` -- narrowed at
# use, never `Any` (python-type-safety); the values are arbitrary JSON already validated by the
# inspect-ai converter that produced them.
JsonObject = dict[str, object]


class Provenance(BaseModel):
    """Per-example provenance for one rejection-sampled trajectory (lands in the manifest).

    ``reward`` is ``Literal[1]``: the SFT set is rejection-sampled to the account-B graded reward 1
    (§8 reward-boundary -- never the env ``step()``), so a record claiming reward 0 is a
    contradiction refused at the boundary. ``verifier_runs`` is the K-reproduction count behind that
    grade (leg-3 replay). Pre-T0 there is no ledger, so no signature id yet (#78: it appears
    when the WORM ledger lands).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    # The inspect eval-task identifier the rollout ran under (EvalSpec.task_id) -- distinguishes two
    # tasks that share a sample id in one eval() run, and records which run produced the trajectory.
    eval_task_id: str
    epoch: int
    model: str
    run_id: str | None
    harness_git_sha: str | None
    reward: Literal[1] = 1
    # The K-reproduction count behind the grade; None when the source log did not record it.
    verifier_runs: int | None


class SFTExample(BaseModel):
    """One positive trajectory: its OpenAI messages+tools transcript + provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    messages: list[JsonObject]
    tools: list[JsonObject]
    provenance: Provenance

    def training_record(self) -> JsonObject:
        """The clean TRL conversational columns -- ``{messages, tools}``, provenance excluded.

        ``tools`` is always present (possibly empty) so every row shares one schema: datasets'
        ``load_dataset("json")`` infers a single schema across rows, and a row missing ``tools``
        while another carries it corrupts the column.
        """
        return {"messages": self.messages, "tools": self.tools}
