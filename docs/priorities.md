# AssayOps — Priorities (what to work on NOW)

> **What this file is.** The live **priority order** — what to build next and why — for a fresh agent
> landing in this repo. It sits *above* the GitHub board (issue detail) and *beside*
> [`DECISIONS.md`](../DECISIONS.md).
>
> - **`DECISIONS.md` = the frozen floor (rules).** Trust model, the 15-vector bar, the eval bar. **Never violated.**
> - **`priorities.md` (this file) = the live order (sequencing).** What to do *first*, given the stage.
> - **GitHub Projects = the tasks.** Epics E0-E15 + issues.
>
> On a conflict about **what to build first**, this file wins over the board. On a **trust rule**,
> `DECISIONS.md` always wins — this file only reorders *when* things get built, never *whether* the
> reward stays un-gameable.
>
> **Agent directive:** work the lowest-numbered incomplete item in **P0 → P1 → P2** order. **Never
> start a P2 item or a Freeze-list item while any P0/P1 item is open.**

**Last set: 2026-07-01.** Re-evaluate when any of these flips: the RL/eval seat closes · a directional
lift number lands · Henry routes an intro.

## Reality check (read before picking up work)

- **We are PRE-T0. The team is NOT closed.** Sam is effectively **solo**. The **RL/eval owner — the
  single load-bearing role — is OPEN** (Shaurya = pitch in progress; Beshr = a *later* DevOps hire,
  task-authoring only, not RL/eval). **The board's `E15-3 = Done` is STALE — the seat is not closed; fix it.**
- **The thesis is validated; the risk is now execution + people** — not "is this right" (yes) but "will
  we get a proof + a buyer + the RL/eval seat before the ~2-3yr consolidation window closes."
- **The failure mode to avoid:** building beautiful trust infrastructure (comfortable, controllable)
  while the two scary, uncontrollable, evidence-producing moves — **get a lift number** and **talk to a
  lab** — sit undone. If the "obvious next infra task" is not on the P0/P1 list below, it's probably
  avoidance. Pick a P0/P1 item.

## The priority order

The board is a **horizontal, subsystem-by-subsystem build**: E2 verifier → E3 adapters → E4 ledger →
E5 env → E6 replay → E7 orch → E8 accounts → E9 guardrails → E10 red-team → *then* E11 corpus → E12 SFT
→ E13 the number. That order makes the **first lift number the LAST artifact** — wrong for a pre-T0
solo team. Do this instead:

### P0 — This week (near-zero build; close the seat + open the door)
1. **Send the Henry scout note** (E15-2). A name + an intro, *not* a pitch. Cheapest, highest-ROI action
   on the board; de-risks the company and is the best ammo to close Shaurya.
2. **Close the RL/eval seat** (the real T0 gate; correct E15-3). Pitch Shaurya as a co-founder who
   *owns* RL/eval + eval design. **Pre-decide the "no" branch before the pitch** (hire an RL/eval owner,
   or reassess whether AssayOps is solo-viable). Do not repeat the Cleno single-point-of-failure — never
   hard-gate the company on one unconfirmed person.
3. **Timebox the LocalStack ↔ real-CFN fidelity / unit-economics spike (#61).** It gates the entire
   grading substrate; know the answer *before* authoring a corpus on it.

### P1 — Weeks 2-4 (a thin vertical slice → a DIRECTIONAL number)
4. **NEW pre-T0 spike: a thin, de-scoped vertical slice to a directional lift number — LocalStack-graded,
   NOT for publication.** (File as one issue; do not confuse with the full-rigor E11/E12/E13.)
   - ~**15 Terraform** drift tasks (subset of E11 / #67 — Terraform, not CDK; CDK waits for Beshr).
   - **SFT a 7B** (Qwen2.5-Coder-7B — *not* the 30B MoE; skips the #64 MoE-LoRA spike).
   - A **noisy number** (n≈15 tasks, 3 seeds) — explicitly **NOT** the pre-registered E13 proof.
   - **Grade with what is already SHIPPED:** E2-1 verifier skeleton, E3-2 Terraform adapter, E2-5 golden
     generator, E2-2 `grade_deployment`. No new trust infra required.
   - **Purpose:** recruit Shaurya (the loop runs end-to-end + there's signal) and tell *us* whether the
     approach has legs — before sinking weeks into the ledger and account pools.
   - **Why this is allowed (respects R1):** the trust-isolation stack (E4 ledger, E8 accounts, E9
     guardrails, E10 red-team) exists to make the reward un-gameable by an **adversarial RL agent** and to
     back a **lab-facing claim**. An **SFT directional number has neither** — no adversarial policy, no
     external claim — so it needs none of E4/E8/E9/E10. **Never publish or pitch this number as the
     proof.** That would break R1.

### P2 — AFTER the seat closes (T0) AND the directional signal is positive: the real proof
Only now complete the horizontal build for the **lab-grade** proof (the un-gameable reward IS required here):
- **Trust infra (the moat):** E2-3/E2-4 reward core + cross-account isolation, E4 ledger, E8 accounts,
  **E9 / T7 guardrails = BLOCKING before any real-AWS episode**, E10 the 15-vector red-team
  (**R1: any open vector ⇒ STOP; no proof claim on a gameable reward**).
- **Corpus + proof:** E11 CDK at N=30-50 (Beshr), E12 SFT on the 30B, E13 the **pre-registered proof**
  (OOD slice, ≥3 seeds, clustered SEs, contamination + **beat-synthetic-baseline** checks, +8-10 pt).
- **Phase 4:** pitch Anthropic via Henry — gated on the proof clearing the bar, not a date.

## Freeze list (until: a Henry reply + a directional number + a Shaurya yes/no)
Do **not** spend effort now on: WORM-ledger signing polish, codegen/contract hardening, account-pool
automation, further Python-first refinement, the leaderboard (E14), env-server polish beyond what the P1
slice needs. You already have enough verifier to grade 15 tasks. **More trust infra right now = avoidance
of the three things that ARE the company: the seat, the number, the lab door.** The full moat gets built
in P2 — not before.

## The one rule this file serves
**Evidence and the team before architecture.** Sequence the cheap, uncontrollable, evidence-producing
moves (recruit, scout, a number) *ahead of* the expensive, controllable, comfortable infra. This never
weakens the trust model — it only reorders when the moat gets built, and keeps the un-gameable reward
mandatory for the real, lab-facing proof.
