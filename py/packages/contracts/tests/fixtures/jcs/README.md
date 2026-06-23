# RFC 8785 (JCS) conformance vectors

`<name>.input.json` → `<name>.output.json` pairs: a JSON value and its expected RFC 8785 (JSON
Canonicalization Scheme) canonical form, byte-exact (no trailing newline). They cover the cases that
separate a conformant canonicalizer from a naive `JSON.stringify`/`json.dumps`: UTF-16 code-unit key
sorting, locale-independent ordering, surrogate-pair and control-character escaping, and ECMAScript
shortest-form number serialization.

**Provenance.** Verbatim from the canonicalization test suite referenced by RFC 8785
(`cyberphone/json-canonicalization`, `testdata/{input,output}`). Public test data, used here to prove a
canonicalizer is spec-conformant.

**Scope.** These are generic *JCS-spec* conformance vectors for the canonicalizer, exercised by the
reward-ledger primitives spike. They are **not** the locked AssayOps contract golden corpus
(`contracts/vectors`) — that corpus and the CI byte-parity gate are owned by the contract-spine work and
land in their own fixture-change PR.
