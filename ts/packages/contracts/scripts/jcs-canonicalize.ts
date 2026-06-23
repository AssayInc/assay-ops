// JCS canonicalization harness: reads a JSON array of values from stdin and writes their RFC 8785 (JCS)
// canonical forms, newline-delimited, to stdout — driving the production TS `canonicalize` (src/jcs.ts).
// The Python cross-language tests (tests/test_jcs_golden_vectors.py + the #115 ledger spike) shell out
// here and assert byte-identity with `rfc8785` (the Python signer) — the Python-signer ↔ TS-consumer
// byte-parity the reward signature depends on (DECISIONS.md I3).
import { canonicalize } from "../src/jcs"

const values = JSON.parse(await Bun.stdin.text()) as unknown[]

// JCS escapes literal newlines, so a canonical form never contains one — newline-delimited is unambiguous.
process.stdout.write(values.map((value) => canonicalize(value)).join("\n"))
