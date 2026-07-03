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

**Last set: 2026-07-02, evening re-set — the directional number landed.** #176 ran all legs
end-to-end: the machine + reward are validated (~200 graded episodes, 0 quarantined/errored,
K=3-reproducible throughout), and the SFT delta came back **flat at a homeopathic dose** —
uninformative on the lift claim, decisive on the bottleneck (hard-task trajectory yield; see
`learnings/2026-07-02-pre-t0-directional-slice.md`). The Henry scout note is **sent** (#24,
awaiting reply). Re-evaluate when any of these flips: the RL/eval seat closes · ~~the
teacher-round signal lands (#186)~~ **LANDED 2026-07-02, not positive — see P1-5** · Henry replies.

## Reality check (read before picking up work)

- **We are PRE-T0. The team is NOT closed.** Sam is effectively **solo**. The **RL/eval owner — the
  single load-bearing role — is OPEN**: **Shaurya declined (2026-07-02)** — the lead candidate fell through,
  so we must **find a new researcher (RL/eval owner)** (Beshr = a *later* DevOps hire, task-authoring only,
  not RL/eval). Per P0-2's pre-decided no-branch this does **not** hard-gate the build — **#176's
  outcome is the ammo for the next candidate**: a working end-to-end loop with a zero-flake,
  fail-closed reward is more credible to a skeptical RL/eval researcher than an undefendable
  small-n lift number would have been. (#25 closed `not planned`: that was the Shaurya pitch, not
  the seat — the seat is still unfilled.)
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
1. ~~**Send the Henry scout note** (E15-2).~~ **SENT 2026-07-02** (#24) — awaiting the reply; log
   the learning on the issue when it lands.
2. **Close the RL/eval seat** (the real T0 gate) — **the one open P0**. New candidate search
   (Shaurya declined); pitch a co-founder who *owns* RL/eval + eval design, with the working
   loop as the ammo. **Pre-decide the "no" branch before each pitch** (hire an RL/eval owner,
   or reassess whether AssayOps is solo-viable). Never hard-gate the company on one unconfirmed
   person.
3. ~~**Timebox the LocalStack ↔ real-CFN fidelity / unit-economics spike (#61).**~~ **RESOLVED**
   (PR #177): LocalStack grading substrate-sound for the CC-graded Terraform corpus; ~$0.04/traj.

### P1 — This week (near-zero build; the experiment that resolves the P2 gate)
4. ~~**Pre-T0 directional slice (#176).**~~ **DONE 2026-07-02** — all legs + the runs; delta flat
   at a homeopathic dose (uninformative on lift, by design underpowered); machine + reward
   validated; the bottleneck named: hard-task trajectory yield from a weak student (1/40).
   Read: `learnings/2026-07-02-pre-t0-directional-slice.md`.
5. ~~**Teacher-distillation round (#186).**~~ **DONE 2026-07-02** — ran end-to-end same day,
   ~$15 total. The signal: **collection validated, training leg negative.** Teacher hard-tier
   CORRECT-rate 83% → 97.5% (budget-matched) through the verifier filter on the tier where the
   student was 1/40 (79 gold examples, tripwire silent); SFT on that set came back **negative**
   (held-out −22.2 pts; a matched-budget diagnostic argues against a budget-only rescue at
   −33.3) — form-not-function transfer at
   7B/LoRA/1-epoch. Read: `learnings/2026-07-02-pre-t0-teacher-distillation.md`. The
   "teacher-round signal lands (#186)" re-evaluation trigger has now flipped (signal ≠ positive
   ⇒ the P2 gate stays closed).

### P2 — AFTER the seat closes (T0) AND a positive training-side signal: the real proof
(#186 landed 2026-07-02 **negative** on the training leg — this gate now awaits a positive
signal from a follow-up leg, per the P1-5 read; the collection leg is validated.)
Only now complete the horizontal build for the **lab-grade** proof (the un-gameable reward IS required here):
- **Trust infra (the moat):** E2-3/E2-4 reward core + cross-account isolation, E4 ledger, E8 accounts,
  **E9 / T7 guardrails = BLOCKING before any real-AWS episode**, E10 the 15-vector red-team
  (**R1: any open vector ⇒ STOP; no proof claim on a gameable reward**).
- **Corpus + proof:** E11 CDK at N=30-50 (Beshr), E12 SFT on the 30B, E13 the **pre-registered proof**
  (OOD slice, ≥3 seeds, clustered SEs, contamination + **beat-synthetic-baseline** checks, +8-10 pt).
- **Phase 4:** pitch Anthropic via Henry — gated on the proof clearing the bar, not a date.

## Freeze list (until: a Henry reply + the seat outcome; the #186 teacher-round signal landed 2026-07-02, not positive)
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
