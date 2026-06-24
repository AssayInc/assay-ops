# tasks/todo.md — #140 Codegen hardening (E1 follow-up from the #29 review)

> Ephemeral per-session scratchpad (lessons.md: durable records go to GitHub/PROGRAM/DECISIONS, not here).

## Grounding outcome (reconciled: code + DECISIONS §2/5A·§4/I3·§8 + ARCHITECTURE + issue/comments)

**The founder's correction comment on #140 is itself stale on its headline item.** `main` (justfile:23-26,
commit `a4be645` inside PR #139, which changed justfile +11/-9) **already globs quicktype** over
`contracts/schemas/*.schema.json` under `LC_ALL=C`. So:
- Issue BODY is *correct* that quicktype was globbed in #29/#139.
- Correction comment's item 1 ("quicktype is NOT globbed; PR #139 never touched justfile") is **wrong vs main** →
  **already done, do NOT redo.** Flag to the user + correct the issue/PROGRAM.
- `just-version` already pinned (ci.yml:87, localstack-smoke.yml:45) → done.

**Genuinely remaining (verified against `main`):**
1. `ts/packages/contracts/tests/schemas.test.ts` hardcodes the 4 names (line 11) → enumerate the dir.
2. justfile reward-pin (lines 31-32) is an unanchored blanket rewrite asserting only ≥1 match → anchor to the
   RewardRecord interface + fail-closed exactly-one guard. (§8 binary-reward invariant — must never drop the pin.)
3. `py/.../assayops_contracts/__init__.py` hand-lists re-exports; `models/__init__.py` is empty → a 3rd
   "won't follow a new schema" list. (comment (4); comment C's bullets omit it but A/B fold it in — in-theme.)
   Fix as a **fail-loud parity test** (NOT dynamic re-export — that breaks mypy-strict re-export visibility).

Not touching: `contracts/vectors` + `tools/red-team` (locked §8); `gen_vectors.py` authored record set;
generated files by hand. `contracts/schemas` editable (not locked) — only a throwaway probe, reverted.

## Plan (TDD: each AC → failing test → green)

- [ ] **AC1 — schemas.test.ts enumerates the dir.** RED: with a throwaway 5th schema, a coverage guard fails
      against the hardcoded list. GREEN: derive the validated set from `readdirSync(contracts/schemas/*.schema.json)`;
      keep the 4 bespoke instance/modeling tests; add a non-tautological guard (non-empty + ⊇ fixtured names).
- [ ] **AC2 — reward-pin anchored.** RED (local fixture, 2 interfaces each with `reward: number;`): old blanket
      perl narrows both. GREEN: scope the rewrite to the `RewardRecord` block + assert exactly-one `reward: number;`
      pre / pin lands post (fail-closed). Then `just codegen` → byte-identical to committed generated.ts.
- [ ] **AC3 — __init__ re-export parity test (py).** RED: throwaway 5th schema → `just codegen` makes a model not
      in `__all__` → test fails. GREEN: every BaseModel/Enum defined under `models/*.py` is in
      `assayops_contracts.__all__` and importable.
- [ ] **Guard (end-to-end).** Throwaway `zzz-probe.schema.json`: `just codegen` → TS interface + Pydantic model
      with NO hardcoded-list edits; schemas.test ajv-validates it; __init__ parity test goes red until exported.
      Remove it; `just codegen` + `just vectors` → `git diff` empty (byte-identical; vectors untouched throughout).
- [ ] `bun run verify` green; `just codegen`/`just vectors` reproduce committed artifacts (codegen-parity gate).
- [ ] Update PROGRAM.md + ISSUES.md; PR `Closes #140` with the quicktype-already-done correction; `/review`.
