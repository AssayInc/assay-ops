---
name: pydantic-v2
description: >
  Author and review Pydantic v2 models — the typed data-validation + serialization layer Python
  services build on. Use it whenever you define or change a `BaseModel`, `Field`, validator,
  `ConfigDict`, `TypeAdapter`, or serialization, configure `pydantic-settings`, wire the
  `pydantic.mypy` plugin, or migrate v1→v2 — even when "Pydantic" isn't named but the task is typed
  validation / parsing / serialization of Python data. CRITICAL for any model whose output is signed,
  hashed, or canonicalized: Pydantic does NOT sort keys and `model_dump_json` is NOT RFC 8785 / JCS
  canonical, so canonicalize `model_dump(mode="json")` with a dedicated canonicalizer before
  hashing/signing. Covers deterministic serialization, `frozen` / `extra="forbid"` / `strict`
  hardening, the mypy-plugin `disallow_any_explicit` gotcha, validators, `TypeAdapter`, settings,
  migration. NOT the JCS/signing recipe itself (use reward-ledger-worm), NOT generic `Any`/type policy
  (use python-type-safety).
compatibility: >
  Self-contained guidance grounded in the official Pydantic v2 docs (pydantic.dev/docs/validation,
  v2.13.x) — no checkout needed. Project rationale (why determinism/canonicalization matter, the
  contract spine) is recalled through the co-located assay-brain skill, a sibling in this repo that
  resolves the brain and degrades gracefully if it isn't checked out. Never hard-code a brain path.
  Designed for Claude Code; portable to any skills-compatible agent.
metadata:
  author: AssayInc
  version: "1.0.0"
  repository: https://github.com/AssayInc/skills
  provenance: "Official Pydantic v2 docs (pydantic.dev/docs/validation/latest, v2.13.4): concepts/serialization, concepts/config, concepts/strict_mode, concepts/validators, concepts/fields, concepts/json_schema, concepts/unions, concepts/type_adapter, concepts/pydantic_settings, integrations/dev-tools/mypy, get-started/migration, and the BaseModel/ConfigDict API reference. Project rationale via assay-brain (the contract spine + the signed-bytes recipe); sibling skills reward-ledger-worm (the JCS/KMS recipe), deterministic-verification, python-type-safety."
---

# Pydantic v2 — typed validation + deterministic serialization

Pydantic v2 validates data against Python type hints (coercing by default) and serializes models back
out; its core is implemented in Rust (`pydantic-core`). It is how a Python service turns untrusted
input into typed objects and typed objects into JSON. This skill is the **correct-by-default** way to
use it — with the emphasis a generic Pydantic tutorial omits: **what you serialize is what gets signed**,
so determinism and hardening are not optional.

> **Stance.** A model whose serialized bytes vary, or silently drop/accept fields, is a latent bug in
> any system that hashes, signs, diffs, or stores that output. When the output is load-bearing
> (a signed record, a canonical diff, a cross-runtime contract), **pin the bytes and harden the model** —
> don't assume Pydantic's defaults give you determinism or strictness. They don't.

## The load-bearing rule: `model_dump_json()` is NOT canonical

This is the one that breaks signing/hashing systems. From the official serialization docs:

- **Pydantic does not sort object keys** and exposes **no `sort_keys` knob.** Keys come out in
  **field-definition order**, not lexicographic order.
- `model_dump_json()` is compact (no spaces) but is **not** RFC 8785 / JCS canonical — its key order
  and number/string formatting are not the JCS spec's.

So **never sign or hash `model_dump_json()` directly.** The correct path for a canonical, cross-runtime
signature: `model_dump(mode="json")` → a dedicated JCS canonicalizer (e.g. `rfc8785`) → UTF-8 → SHA-256
→ sign. `mode="json"` guarantees **only JSON-serializable types** (datetime→ISO string, tuple→list,
`Decimal`→string, etc.); `mode="python"` (the default) may leave non-JSON objects in the dict. The
canonical-bytes recipe itself lives in **reward-ledger-worm**; this skill's job is to make the Pydantic
dict feeding it deterministic.

Three more serialization traps that change the bytes:
- **Omitted-optional / `exclude_unset` is input-dependent.** `exclude_unset=True` drops fields that
  weren't explicitly set (tracked by `model_fields_set`), so two semantically-equal models built
  differently dump differently. For a signed record, **prefer required fields** or a fixed dump shape.
- **Subclass extras are silently dropped.** A subclass instance in a base-typed field serializes **as
  the base type** — extra fields vanish (changed from v1). What you sign depends on the *declared* field
  type, not the runtime object. Opt in deliberately when you want the extras: v2.13's
  **`polymorphic_serialization`** — the `ConfigDict` option (model/dataclass-scoped) or the `model_dump`
  runtime arg (applies to all nested types, overrides config); preferred over the broader
  `serialize_as_any=True` / `SerializeAsAny[T]`.
- **Union member at serialization is underdocumented.** Which union member serializes is not
  contractually specified — use **discriminated unions** (`Field(discriminator=...)`) when the dumped
  shape must be deterministic.

Set **`model_config = ConfigDict(ser_json_inf_nan="strings")`** and validation **`allow_inf_nan=False`**
if inf/NaN could appear — the default silently maps them to `null` on dump. Pass **`warnings="error"`**
to `model_dump`/`model_dump_json` so a serialization/duck-typing mismatch raises instead of emitting
suspect bytes.

## Harden the model — the defaults are permissive

`ConfigDict` defaults are tuned for ergonomics, not for a trust boundary. For any contract/record model:

```python
from pydantic import BaseModel, ConfigDict

class RewardRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    ...
```

- **`extra="forbid"`** (default `"ignore"`) — reject unexpected fields. The default **silently drops**
  them, so a typo'd or injected key passes unnoticed. For anything parsed from an untrusted/wire source,
  forbid.
- **`frozen=True`** (default `False`) — faux-immutable: blocks `__setattr__` (raises `ValidationError`,
  `frozen_instance`) and **generates `__hash__`** (hashable only if **all** field values are hashable — a
  `dict`/`list` field makes `hash()` raise). Note it does **not** deep-freeze — mutating a nested
  `dict`/`list` in place still works; freeze the contents too if that matters.
- **`strict=True`** (default `False`) — disables **most** coercion; a value must generally already match
  the type (not absolute — e.g. `int`→`float` is still accepted in strict; consult the conversion table).
  **Gotcha:** strict is also **looser for JSON input** — `validate_json` still accepts a date/UUID/Decimal as
  a string even in strict mode (JSON has no native type), whereas `validate_python` rejects it. Don't
  assume `strict=True` means "string never becomes a date."
- `revalidate_instances="always"` if a passed-in model instance must be re-proven (default `"never"`
  trusts it).

Validate methods: `model_validate()` (Python obj), **`model_validate_json()`** (JSON — usually faster
than `json.loads` + validate, and is the strict-JSON path above), `model_validate_strings()`.
**`model_construct()` skips validation entirely** — only for already-trusted data.

## The `pydantic.mypy` plugin — and the `disallow_any_explicit` gotcha

Enable the plugin so mypy understands synthesized `__init__`/`model_construct` signatures, `Field`
defaults, frozen models, and untyped-field warnings:

```toml
[tool.mypy]
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]      # NOTE: a separate section from [tool.mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

**The gotcha that bites a hardened mypy config:** the plugin synthesizes an `__init__` containing `Any`
annotations, so **`disallow_any_explicit = true` will error inside Pydantic models** unless you enable
**both `init_typed` and `init_forbid_extra`** (verbatim from the plugin docs) — the repo-wide fix. The
plugin drops the synthesized `Any` *per model* whenever the model is already **`strict=True`** (covers
`init_typed`) **and `extra='forbid'`** (covers `init_forbid_extra`) — so the hardened combo above earns
this for free; set both plugin flags so even un-hardened models pass. A repo that bans explicit `Any`
(see **python-type-safety**) and uses Pydantic should do this. (Alternatively, scope a per-module
`disallow_any_explicit = false` override onto the model package — the pragmatic route when the models are
codegen output you don't hand-type.)

## Define fields and validators the modern way

- **`Annotated[T, Field(...)]`** is the preferred field form (reusable, type-checker-clear) — **except**
  `default`, `default_factory`, and `alias`, which static checkers only synthesize from the
  `x: T = Field(default=...)` assignment form. Use assignment for those three.
- **`con*` functions (`conint`, `constr`, …) are discouraged** (they return a type, opaque to static
  analysis; slated for deprecation in Pydantic 3.0) → use `Annotated[int, Field(strict=True, gt=0)]` or
  `annotated_types` markers (`Gt`, `Len`, …).
- **`Optional[T]` is REQUIRED in v2** — `x: Optional[str]` is a required field that allows `None`; it is
  **not** a default of `None`. Write `x: str | None = None` for optional-with-default.
- Validators: `@field_validator('f', mode='before'|'after'|'wrap'|'plain')` (a `@classmethod`) or, for
  reuse, **annotated validators** (`Annotated[int, AfterValidator(fn)]`). `@model_validator(mode='after')`
  is an **instance method that must `return self`**. Raise `ValueError`/`PydanticCustomError` (not
  `TypeError`) to signal invalid; all are aggregated into one `ValidationError`.
- `SecretStr`/`SecretBytes` for credentials — they render as `'**********'` in `repr`/`str` and serialize
  masked; read with `.get_secret_value()`.

## Beyond BaseModel

- **`TypeAdapter(T)`** validates/serializes non-`BaseModel` types (`list[Model]`, `TypedDict`, unions,
  dataclasses): `TypeAdapter(list[Person]).validate_json(text)`. **Instantiate once and reuse** —
  construction has non-trivial overhead. Note `dump_json()` returns **`bytes`** (vs `model_dump_json`'s
  `str`).
- **`pydantic-settings`** (separate package): `BaseSettings` + `SettingsConfigDict` for typed config from
  env / dotenv / secrets-dir, with `SecretStr` fields. Source priority (high→low): CLI (when
  `cli_parse_args` is enabled) > init args > env > dotenv > file secrets > defaults; reorder via
  `settings_customise_sources`. Unlike `BaseModel`, **defaults are validated** here.

## Anti-patterns

| Tempting shortcut | Why it's wrong | Instead |
|---|---|---|
| Sign/hash `model.model_dump_json()`. | Not JCS-canonical — no key sort; format isn't the spec's. Cross-runtime/byte mismatch. | `model_dump(mode="json")` → dedicated JCS canonicalizer → hash/sign (`reward-ledger-worm`). |
| Leave `extra` at its default for a wire/contract model. | Default `"ignore"` silently drops unknown keys — typos/injection pass. | `ConfigDict(extra="forbid")`. |
| Assume `model_dump()` is JSON-safe. | Default `mode="python"` leaves `datetime`/`Decimal`/`tuple` as Python objects. | `model_dump(mode="json")`. |
| Trust `exclude_unset` / a sparse shape to be stable for signing. | `exclude_unset` output depends on how the model was built; field order is preserved but still worth pinning. | Required fields + a fixed dump shape; lock byte-stability with a golden test. |
| `disallow_any_explicit=true` + Pydantic, plugin half-configured. | Plugin's synthesized `__init__` has `Any` → every model errors. | Enable `init_typed` AND `init_forbid_extra`. |
| `x: Optional[str]` expecting an optional field. | In v2 that's **required**, allowing `None`. | `x: str | None = None`. |
| `conint(gt=0)` / `constr(...)`. | Discouraged (slated for deprecation in Pydantic 3.0); opaque to static analysis. | `Annotated[int, Field(strict=True, gt=0)]`. |
| `strict=True` ⇒ "a string can't become a date". | Strict is **looser for JSON** input. | Validate via `model_validate` (Python) when you need the strict-Python rule; know `validate_json` still coerces JSON strings. |

## Prove it or flag it

- **Byte-stability is a test, not a hope.** For any signed/hashed model, assert `canonicalize(dump) ==`
  a committed golden across constructions/runtimes — the same model must produce the same canonical
  bytes (this is the contract the reward ledger and cross-runtime parity rest on).
- **Harden by default** for contract/record/wire models: `frozen`, `extra="forbid"`, `strict` — then
  relax deliberately, per field, with a reason.
- If a field is genuinely an **open JSON object**, type it `dict[str, object]` (not `Any` — see
  **python-type-safety**) and validate at the boundary; don't smuggle untyped data through a model.
- If serialized output must be JCS-canonical, the canonicalization is **not Pydantic's job** — flag it to
  the signing layer (**reward-ledger-worm**); Pydantic only produces the JSON-safe dict.

## Going deeper

**Deep reference** — the concept-by-concept detail (the `model_dump`/`ConfigDict` args with
defaults, validator modes + `ValidationInfo`, the strict conversion table, JSON-schema generation, the
complete v1→v2 migration map, dataclasses, `validate_call`, performance tips) is in
**`references/pydantic-v2-reference.md`**. Read it when the SKILL.md summary above isn't specific enough.

**Official docs** (ground every API claim here, never cached memory): `pydantic.dev/docs/validation/latest/`
— `concepts/serialization`, `concepts/config`, `concepts/strict_mode`, `concepts/validators`,
`concepts/fields`, `concepts/type_adapter`, `concepts/pydantic_settings`,
`integrations/dev-tools/mypy`, `get-started/migration`, and the `api/pydantic/base_model` +
`api/pydantic/config` reference for authoritative arg defaults.

**Project rationale.** Why deterministic serialization is load-bearing (the contract spine; the signed
record keyed by `trajectory_id`) lives in the brain — recall via **assay-brain**. The JCS → SHA-256 →
KMS recipe is **reward-ledger-worm**; the `Any`/`object` boundary policy is **python-type-safety**.
