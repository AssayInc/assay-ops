import jsonCanonicalize from "canonicalize"

// RFC 8785 (JCS) canonicalization for the TS consumer of the contract spine — the public/web binding's
// half of the byte-parity gate (DECISIONS.md I3). The account-B reward ledger (Python) signs over the
// JCS bytes of a record; a TS consumer (assay-web / a TS lab) canonicalizes the same record this way to
// verify the signature, so the bytes must be identical to the Python signer's `rfc8785`. The locked
// corpus contracts/vectors/jcs-golden.json pins that parity (regenerate via `just vectors`).

/**
 * The RFC 8785 (JCS) canonical JSON string of a contract record — the exact bytes the reward ledger
 * signs (record → JCS → UTF-8 → SHA-256 → KMS Sign). Throws if the value is not JSON-serializable
 * (npm `canonicalize` returns `undefined` for `undefined`/function inputs); a contract record never is.
 *
 * Canonicalize the MATERIALIZED record (the Python signer's `model_dump` form), not a hand-built sparse
 * object: re-derive from the same materialized record, or verify over the stored canonical payload bytes.
 *
 * Numbers must be IEEE-754-representable, strings valid Unicode (the contract models large values as
 * strings). The Python signer's `rfc8785` fails closed on a violation; JS rounds/escapes instead, so a
 * verifying consumer must reject out-of-domain values before verifying — tracked for E4/#29.
 */
export function canonicalize(value: unknown): string {
  const canonical = jsonCanonicalize(value)
  if (canonical === undefined) {
    throw new Error("canonicalize: value is not JSON-serializable")
  }
  return canonical
}
