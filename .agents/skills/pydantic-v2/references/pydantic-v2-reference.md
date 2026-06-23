# Pydantic v2 — reference

Concept-by-concept detail backing the `SKILL.md` summary. Grounded in the official docs
(`pydantic.dev/docs/validation/latest/`, v2.13.x) + the BaseModel/ConfigDict API reference. Read the
section you need; the SKILL.md covers the load-bearing rules inline.

## Contents
1. Serialization (args, determinism, custom serializers)
2. Config / ConfigDict (key options + defaults)
3. Strict mode + the conversion table
4. Validators
5. Fields
6. Types
7. JSON Schema
8. Unions
9. TypeAdapter
10. Dataclasses & validate_call
11. pydantic-settings
12. Performance
13. v1 → v2 migration map

---

## 1. Serialization

`model_dump(...)` → dict; `model_dump_json(...)` → **str** (compact by default; `indent=None`). Common
`model_dump` args (all default off unless noted; the full set incl. `ensure_ascii`, `fallback`,
`exclude_computed_fields`, `polymorphic_serialization` is in the BaseModel API ref):

| Arg | Effect | Default |
|---|---|---|
| `mode` | `'json'` → only JSON-serializable types (datetime→ISO str, tuple→list, Decimal→str); `'python'` → may contain non-JSON objects | `'python'` |
| `include`/`exclude` | field selection; set = whole field, dict = descend, int keys index lists, `'__all__'` = each element | `None` |
| `by_alias` | use field aliases as keys (`None` = off, unless `ConfigDict(serialize_by_alias=True)`) | `None` |
| `exclude_unset` | drop fields not explicitly set (tracked by `model_fields_set`) — **output depends on construction** | `False` |
| `exclude_none` | drop fields whose value is `None` | `False` |
| `exclude_defaults` | drop fields equal (`==`) to their default | `False` |
| `round_trip` | output is valid as re-input for non-idempotent types (`Json[T]`) | `False` |
| `warnings` | `False`/`'none'` ignore, `True`/`'warn'` log, **`'error'` raises `PydanticSerializationError`** | `True` |
| `serialize_as_any` | duck-typing serialization (include subclass extras) | `False` |
| `context` | extra context passed to serializers | `None` |
| `model_dump_json` `indent` | `None` → compact | `None` |

**Determinism notes (load-bearing for signing/hashing):**
- **No key sorting, no `sort_keys`.** Keys emit in field-definition order. `model_dump_json()` is **not**
  RFC 8785 / JCS canonical → canonicalize `model_dump(mode='json')` with `rfc8785` before signing.
- Field order follows field-definition order (preserved on serialization); still lock the exact bytes
  with a golden test for any signed artifact.
- `exclude_unset`/`exclude_none`/`exclude_defaults` make output input-dependent → for signed records,
  prefer required fields + a fixed shape.
- **Subclass extras dropped:** a subclass in a base-typed field serializes as the base type. Opt in with
  v2.13's `polymorphic_serialization` — the ConfigDict option (model/dataclass-scoped) or the `model_dump`
  runtime arg (all nested types, overrides config); preferred over the broader `serialize_as_any=True` /
  `SerializeAsAny[T]`. Only when intended.
- **Union member at serialization is not contractually specified** → use discriminated unions when the
  dumped shape must be deterministic.
- `model_dump_json()` uses pydantic-core's Rust serializer directly (handles datetime/UUID natively);
  `json.dumps(model.model_dump())` can choke on `mode='python'` non-JSON objects. `TypeAdapter(...)
  .dump_json()` returns **bytes**, not str.

**Custom serializers:** `@field_serializer('f', mode='plain'|'wrap', when_used=...)`;
`@model_serializer(mode='plain'|'wrap')` (a wrap model-serializer gives full control of emitted
shape/key order — the clean hook if you need a deterministic custom shape); annotated `PlainSerializer`/
`WrapSerializer`.

## 2. Config / ConfigDict

Set via `model_config = ConfigDict(...)` (class attribute), `class Model(BaseModel, frozen=True)`
(kwargs; recognized by type checkers), `@with_config` (TypedDict/stdlib dataclass), or `config=` on
`TypeAdapter`/`@pydantic.dataclasses.dataclass` (not allowed when the wrapped type carries its own config). The v1 inner `class Config` is deprecated.

| Option | Effect | Default |
|---|---|---|
| `extra` | `'ignore'`/`'allow'`/`'forbid'` extra fields | `'ignore'` |
| `frozen` | block `__setattr__` (faux-immutable) + generate `__hash__` | `False` |
| `strict` | no coercion globally (overridable per field) | `False` |
| `validate_assignment` | re-validate on attribute set | `False` |
| `validate_default` | validate default values | `False` |
| `revalidate_instances` | `'never'`/`'always'`/`'subclass-instances'` — re-validate passed-in model instances | `'never'` |
| `validate_by_name` | allow populating by field name (v2.11+; replaces `populate_by_name`) | `False` |
| `validate_by_alias` | allow populating by alias (v2.11+) | `True` |
| `use_enum_values` | store `.value` instead of the enum member | `False` |
| `arbitrary_types_allowed` | allow non-pydantic types | `False` |
| `ser_json_bytes` / `val_json_bytes` | `'utf8'`/`'base64'`/`'hex'` — **must be equal** for round-trip | `'utf8'` |
| `ser_json_inf_nan` | `'null'`/`'constants'`/`'strings'` — default silently maps ±inf/NaN→`null` | `'null'` |
| `allow_inf_nan` | allow inf/NaN into float/Decimal at validation | `True` |
| `coerce_numbers_to_str` | (lax only) | `False` |
| `hide_input_in_errors` | keep input values out of error messages | `False` |
| `str_strip_whitespace`/`str_to_lower`/`str_to_upper`/`str_min_length`/`str_max_length` | string transforms/constraints | — |
| `protected_namespaces` | default changed v2.10 → `('model_validate','model_dump')` | — |
| `alias_generator` | callable or `AliasGenerator(...)` | `None` |
| `polymorphic_serialization` | (v2.13) include subclass extras for model/dataclass fields — preferred over `serialize_as_any` | `False` |

**`populate_by_name` use is not recommended in v2.11+** (deprecated in v3) → use `validate_by_name` + `validate_by_alias` (cannot both
be `False`). Multiple bases: Pydantic does **not** follow MRO for config merging.

## 3. Strict mode + conversion

Enable strict 4 ways: call-time (`model_validate(data, strict=True)`, `validate_json(..., strict=True)`),
field-level (`Field(strict=True)`), the `Strict()` annotation (or `StrictInt/Str/Bool/Float/Bytes`),
or `ConfigDict(strict=True)`.

**Gotcha — strict is LOOSER for JSON:** "looser rules may apply to JSON input (for instance, the date
and time types allow strings even in strict mode)." `validate_python('2000-01-01', strict=True)` on a
`date` field **raises**; `validate_json('"2000-01-01"', strict=True)` **succeeds** — JSON has no native
date/UUID/bytes/Decimal, so strict permits the string form there.

Conversion table notes: `bool`→`int`/`float` is accepted in **lax** mode but **forbidden in strict**; `float`→`int` only if
`val % 1 == 0` (rejects nan/inf); numeric `str`/`bytes` must be regex-clean; for `bytes`/`Decimal`, a
`str` is accepted in strict **only from JSON**.

## 4. Validators

- `@field_validator('a','b', mode='before'|'after'|'wrap'|'plain')` — a `@classmethod`, `(cls, value[, info])`.
  `after` (default; runs post-internal-validation, type-safe), `before` (pre-coercion), `plain`
  (before + terminates), `wrap` (runs around a `handler`). Wildcard `'*'`; `check_fields=False`.
- **Annotated validators (preferred for reuse):** `Annotated[int, AfterValidator(fn)]` (also
  `BeforeValidator`/`WrapValidator`/`PlainValidator`) — plain functions, no `cls`.
- `@model_validator(mode='after')` — **instance method, must `return self`**; `mode='before'` —
  classmethod on raw input (guard `isinstance(data, dict)`); `mode='wrap'` — classmethod with a handler.
- **`ValidationInfo`** (`info`): `info.data` (fields validated *before* this one; `None` for model
  validators), `info.context`, `info.field_name`, `info.config`, `info.mode`.
- Raise `ValueError`/`AssertionError`(skipped under `-O`)/`PydanticCustomError` → aggregated into one
  `ValidationError`. Ordering: before+wrap right-to-left, after left-to-right. Defaults aren't validated
  unless `validate_default`.

## 5. Fields

- `Field(default, default_factory, alias, validation_alias, serialization_alias, title, description,
  gt/ge/lt/le/multiple_of, min_length/max_length/pattern, max_digits/decimal_places, frozen, exclude,
  repr, strict, discriminator, init/init_var/kw_only, validate_default)`.
- **`Annotated[T, Field(...)]` preferred — EXCEPT** `default`/`default_factory`/`alias`, which static
  checkers only synthesize from the `x: T = Field(default=...)` assignment form. `x: T = Field(...)` can
  mislead readers into thinking there's a default when the field is still required.
- **`default_factory`** can take validated data (v2.10+): `Field(default_factory=lambda data: data['x'])`
  (reads fields declared before it). Mutable literal defaults are deep-copied per instance.
- Alias precedence: `validation_alias` > `alias` (input); `serialization_alias` > `alias` (output).
  `AliasPath('names', 0)` (nested), `AliasChoices('a','b')` (multiple); `to_camel`/`to_pascal`/`to_snake`
  from `pydantic.alias_generators`.

## 6. Types

- `Annotated[int, Field(gt=0)]` / `annotated_types` markers (`Gt`, `Lt`, `Ge`, `Le`, `Len`, `MultipleOf`).
  Convenience: `PositiveInt`, `NonNegativeInt`, `FiniteFloat`, etc.
- **`con*` functions (`conint`/`constr`/…) are discouraged** (return a type; opaque to static analysis;
  slated for deprecation in Pydantic 3.0) → use `Annotated[...]`.
- `StrictInt/Str/Bool/Float/Bytes` = `Annotated[base, Strict()]`. `SecretStr`/`SecretBytes` (render
  `'**********'`; `.get_secret_value()`). `Json[T]`, `UUID1/3/4/5/6/7/8`, `Aware/Naive/Past/FutureDatetime`,
  `ByteSize`, `ImportString`, `Base64Bytes/Str`, `JsonValue`, `FilePath`/`DirectoryPath`.
- Custom types: `__get_pydantic_core_schema__` (less-stable surface), `GetPydanticSchema` (inline),
  `__get_pydantic_json_schema__`. `EmailStr`/`NameEmail` need the `email` extra.

## 7. JSON Schema

- `model_json_schema(by_alias=True, ref_template=..., mode='validation')` — **`by_alias` defaults `True`**
  (schema keys use aliases unless `by_alias=False`). `TypeAdapter(T).json_schema()` for other types.
- Spec: **Draft 2020-12 / OpenAPI 3.1**. `mode='validation'` vs `'serialization'` differ when in/out
  types differ (e.g. `Decimal` accepts number|string in, emits string out).
- Customize: `Field(json_schema_extra=...)` (dict or callable), `WithJsonSchema(...)`, `SkipJsonSchema`,
  `GenerateJsonSchema` subclass. Pydantic sorts schema keys alphabetically **but** preserves `properties`
  order (= field-definition order).

## 8. Unions

- **`union_mode='smart'` is the default** — evaluates members then ranks by #valid-fields + exactness
  tier (for `BaseModel`/dataclass/`TypedDict` unions all members are tried; a non-model exact match can
  short-circuit). `Field(union_mode='left_to_right')` opt-in (first member that validates wins — lax
  coercion makes `Union[int,str]` + `'456'` → `int`).
- **Discriminated unions:** `Field(discriminator='pet_type')` with `Literal` tags, or
  `Discriminator(callable)` + `Annotated[Cat, Tag('cat')]`. Faster + scoped errors + deterministic
  serialization. The callable runs for both validation and serialization.

## 9. TypeAdapter

Validate/serialize/schema for non-`BaseModel` types: `validate_python`, `validate_json`,
`validate_strings`, `dump_python`, **`dump_json` (returns bytes)**, `json_schema`. **Instantiate once and
reuse** (non-trivial construction overhead). `config=ConfigDict(...)` (not when wrapping a type that has
its own config); `defer_build=True` + `rebuild()`.

## 10. Dataclasses & validate_call

- `@pydantic.dataclasses.dataclass` — stdlib-dataclass-like + validation; config via `config=` or
  `__pydantic_config__` (**not** `model_config`). `__post_init__` runs **between** before- and
  after-validators. No `model_dump`/`model_validate` on the dataclass — wrap with `TypeAdapter`.
- `@validate_call` — validates args against annotations before the call (coerces by default);
  `validate_return=True` also validates the return. Raises `ValidationError` (not `TypeError`).

## 11. pydantic-settings

`pip install pydantic-settings`; `from pydantic_settings import BaseSettings, SettingsConfigDict`.
Env (`env_prefix`, `case_sensitive`), dotenv (`env_file`), secrets dir (`secrets_dir='/run/secrets'`),
nested (`env_nested_delimiter='__'`), CLI source. Priority high→low: **CLI (when `cli_parse_args` is
enabled) > init args > env > dotenv > file secrets > defaults** (reorder via `settings_customise_sources`). Use `SecretStr` for secret fields. Unlike
`BaseModel`, **defaults are validated**.

## 12. Performance (the 9 official tips)

1. `model_validate_json()` not `model_validate(json.loads(...))`. 2. Instantiate `TypeAdapter` once.
3. Prefer concrete `list`/`dict` over `Sequence`/`Mapping`. 4. Use `Any` to skip validation where safe.
5. Avoid primitive subclasses for extra info — use a model field. 6. Tagged (discriminated) unions over
plain unions. 7. `TypedDict` over nested models (~2.5× faster). 8. Avoid wrap validators (materialize
data in Python). 9. `Annotated[list[bool], FailFast()]` to stop on first bad item.

## 13. v1 → v2 migration map

Tool: `pip install bump-pydantic && bump-pydantic my_package`. Compat: `from pydantic.v1 import ...`
(no mixing v1/v2). Method renames: `construct→model_construct`, `copy→model_copy`, `dict→model_dump`,
`json→model_dump_json`, `parse_obj→model_validate`, `update_forward_refs→model_rebuild`,
`schema→model_json_schema`, `__fields__→model_fields`. Deprecated-not-renamed: `parse_raw`/`parse_file`
(→ read + `model_validate_json`), `from_orm`→`model_validate(..., from_attributes=True)`,
`@validate_arguments`→`@validate_call`. `class Config`→`model_config=ConfigDict(...)`. Validators:
`@validator`→`@field_validator`, `@root_validator`→`@model_validator`, `pre=True`→`mode='before'`,
`each_item` removed (annotate the inner type), signature `(cls,v,values,config,field)`→`(cls,v,info)`.
**`Optional[T]` is REQUIRED** (allows `None`, no default). `__root__`→`RootModel`; `GenericModel`→
`BaseModel, Generic[T]`; `min_items`/`max_items`/`regex`→`min_length`/`max_length`/`pattern`;
`const`/`unique_items` removed. `BaseSettings`→`pydantic_settings`; `Color`/`PaymentCardNumber`→
`pydantic_extra_types`. `model_dump_json()` output is compacted.
