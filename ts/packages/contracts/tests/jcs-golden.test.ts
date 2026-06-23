import { describe, expect, test } from "bun:test"
import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import Ajv2020, { type AnySchemaObject, type ValidateFunction } from "ajv/dist/2020"
import { canonicalize } from "../src/jcs"

// The locked JCS golden corpus + the neutral schemas both live at the repo root (contracts/), four
// levels above this test file. The corpus (record -> canonical RFC 8785 bytes -> sha256) is regenerated
// by `just vectors` and editable only in a fixture-change PR (DECISIONS.md §8). This is the TS-consumer
// half of the Python-signer ↔ TS-consumer byte-parity gate (DECISIONS.md I3).
const CONTRACTS_DIR = join(import.meta.dir, "../../../../contracts")
const GOLDEN = join(CONTRACTS_DIR, "vectors/jcs-golden.json")
const SCHEMA_DIR = join(CONTRACTS_DIR, "schemas")

interface Vector {
  name: string
  schema: string
  record: unknown
  canonical: string
  sha256: string
}

const vectors = (JSON.parse(readFileSync(GOLDEN, "utf8")) as { vectors: Vector[] }).vectors

// One shared Ajv instance; compile each schema once (the ajv.js.org idiomatic pattern), as in schemas.test.ts.
const ajv = new Ajv2020({ allErrors: true })
const validators = new Map<string, ValidateFunction>()
function validatorFor(schema: string): ValidateFunction {
  const cached = validators.get(schema)
  if (cached) {
    return cached
  }
  const compiled = ajv.compile(
    JSON.parse(readFileSync(join(SCHEMA_DIR, `${schema}.schema.json`), "utf8")) as AnySchemaObject,
  )
  validators.set(schema, compiled)
  return compiled
}

describe("JCS golden vectors (E1-3)", () => {
  test("the locked corpus is present and non-empty", () => {
    expect(vectors.length).toBeGreaterThan(0)
  })

  for (const v of vectors) {
    describe(v.name, () => {
      test("the record is a valid contract instance (ajv, neutral schema)", () => {
        const validate = validatorFor(v.schema)
        const ok = validate(v.record)
        expect(validate.errors ?? []).toEqual([])
        expect(ok).toBe(true)
      })

      test("the TS consumer reproduces the locked canonical bytes (== Python signer)", () => {
        expect(canonicalize(v.record)).toBe(v.canonical)
      })

      test("the canonical bytes hash to the locked sha256 (the signed digest)", () => {
        expect(createHash("sha256").update(v.canonical, "utf8").digest("hex")).toBe(v.sha256)
      })
    })
  }
})
