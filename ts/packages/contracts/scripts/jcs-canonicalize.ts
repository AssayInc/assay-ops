// JCS parity harness (E17-S2 / #115 spike). Reads a JSON array of values from stdin and writes their
// RFC 8785 (JCS) canonical forms, newline-delimited, to stdout. The Python spike
// (tests/test_ledger_primitives_spike.py) asserts these are byte-identical to `rfc8785` (the Python
// signer's canonicalizer) — the Python-signer ↔ TS-consumer byte-parity the reward signature depends on.
// `canonicalize` (erdtman) is the RFC 8785 reference JS implementation; the production TS canonicalize +
// the CI byte-parity gate are the contract spine's job (this only proves cross-runtime feasibility).
import canonicalize from "canonicalize"

const values = JSON.parse(await Bun.stdin.text()) as unknown[]

const canonical = values.map((value, index) => {
  const out = canonicalize(value)
  if (out === undefined) {
    throw new Error(`canonicalize returned undefined for input at index ${index}`)
  }
  return out
})

// JCS escapes literal newlines, so a canonical form never contains one — newline-delimited is unambiguous.
process.stdout.write(canonical.join("\n"))
