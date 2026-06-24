import { describe, expect, test } from "bun:test"
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import Ajv2020, { type AnySchemaObject, type ValidateFunction } from "ajv/dist/2020"

// The contract schemas are the neutral source of truth at the repo root (contracts/schemas),
// codegen'd to both lanes in E1-2 (#27). This test file sits at ts/packages/contracts/tests —
// four levels below the repo root.
const SCHEMA_DIR = join(import.meta.dir, "../../../../contracts/schemas")

// Discover every schema from disk so a newly added schema is ajv-validated automatically — no hardcoded
// list to forget (#140 codegen hardening). `just codegen`'s quicktype + datamodel-codegen already read the
// whole dir; this aligns the TS ajv coverage with them.
const ALL_SCHEMA_NAMES: string[] = readdirSync(SCHEMA_DIR)
  .filter((f) => f.endsWith(".schema.json"))
  .map((f) => f.slice(0, -".schema.json".length))
  .sort()

// The schemas with bespoke instance fixtures + modeling-rule tests below. The validity/compile coverage
// runs over every schema on disk (ALL_SCHEMA_NAMES); these four add semantic, schema-specific assertions.
const FIXTURED_NAMES = ["reward-record", "trajectory", "diff-ir", "task-spec"] as const
type SchemaName = (typeof FIXTURED_NAMES)[number]

function loadSchema(name: string): AnySchemaObject {
  return JSON.parse(readFileSync(join(SCHEMA_DIR, `${name}.schema.json`), "utf8")) as AnySchemaObject
}

// One shared Ajv instance — `compile` caches each schema, so compile each once and reuse it (the ajv.js.org
// API docs' idiomatic pattern). When codegen (#27) produces the TS types, `ajv.compile<T>` makes the
// validator a type guard (`data is T`) for type-safe validation in the verifier/ledger.
const ajv = new Ajv2020({ allErrors: true })
const validators = new Map<string, ValidateFunction>()

function validatorFor(name: string): ValidateFunction {
  const cached = validators.get(name)
  if (cached) {
    return cached
  }
  const validate = ajv.compile(loadSchema(name))
  validators.set(name, validate)
  return validate
}

// One well-formed instance per schema, with the modeling rules applied (string ids / nonces /
// timestamps, bounded reward). The reject-cases below mutate these.
const VALID: Record<SchemaName, Record<string, unknown>> = {
  "reward-record": {
    trajectory_id: "traj-01J9Z3K8QmR2",
    attempt: 0,
    reward: 1,
    reportDigest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    graderVersion: "grader@1.0.0",
    gradedAt: "1782518400000000000",
    nonce: "5f4dcc3b5aa765d61d8327deb882cf99",
  },
  trajectory: {
    trajectory_id: "traj-01J9Z3K8QmR2",
    task_id: "task-s3-versioning-001",
    createdAt: "1782518400000000000",
    steps: [{ index: 0, observation: {}, action: {} }],
  },
  "diff-ir": {
    resources: [
      { address: "AppBucket", type: "AWS::S3::Bucket", change: "unchanged", propertyDiffs: [] },
    ],
  },
  "task-spec": {
    task_id: "task-s3-versioning-001",
    title: "Enable versioning on the app S3 bucket",
    description: "Deploy an S3 bucket with versioning enabled.",
    tool: "terraform",
    seed: "seed-9a3f1c2e",
  },
}

describe("contract schemas (E1-1)", () => {
  // Runs over EVERY schema on disk (not a hardcoded list): a newly added schema is automatically
  // checked for Draft-2020-12 shape + ajv-compiled here, with no edit to this file (#140).
  describe("each is a valid Draft 2020-12 schema", () => {
    for (const name of ALL_SCHEMA_NAMES) {
      test(name, () => {
        const schema = loadSchema(name)
        expect(schema.$schema).toBe("https://json-schema.org/draft/2020-12/schema")
        expect(typeof schema.$id).toBe("string")
        expect(schema.additionalProperties).toBe(false)
        expect(() => validatorFor(name)).not.toThrow()
      })
    }
  })

  describe("schema discovery is disk-derived (codegen hardening, #140)", () => {
    test("covers every *.schema.json on disk, not a hardcoded subset", () => {
      // Compare the full sorted name set (not just the count) so a same-length but divergent list
      // — e.g. a future regression back to a hardcoded list — fails, not just a count mismatch.
      const onDisk = readdirSync(SCHEMA_DIR)
        .filter((f) => f.endsWith(".schema.json"))
        .map((f) => f.slice(0, -".schema.json".length))
        .sort()
      expect(ALL_SCHEMA_NAMES).toEqual(onDisk)
      expect(ALL_SCHEMA_NAMES.length).toBeGreaterThanOrEqual(FIXTURED_NAMES.length)
    })

    test("the bespoke-fixture schemas are all present on disk", () => {
      for (const name of FIXTURED_NAMES) {
        expect(ALL_SCHEMA_NAMES).toContain(name)
      }
    })
  })

  describe("a well-formed instance validates", () => {
    for (const name of FIXTURED_NAMES) {
      test(name, () => {
        const validate = validatorFor(name)
        const ok = validate(VALID[name])
        expect(validate.errors ?? []).toEqual([])
        expect(ok).toBe(true)
      })
    }
  })

  describe("reward-record modeling rules", () => {
    const base = VALID["reward-record"]

    test("accepts the binary reward values 0 and 1", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, reward: 0 })).toBe(true)
      expect(validate({ ...base, reward: 1 })).toBe(true)
    })

    test("rejects a NaN reward", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, reward: Number.NaN })).toBe(false)
    })

    test("rejects an infinite reward", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, reward: Number.POSITIVE_INFINITY })).toBe(false)
      expect(validate({ ...base, reward: Number.NEGATIVE_INFINITY })).toBe(false)
    })

    test("rejects non-binary rewards — partial credit and out-of-range", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, reward: 0.5 })).toBe(false)
      expect(validate({ ...base, reward: 2 })).toBe(false)
      expect(validate({ ...base, reward: -0.5 })).toBe(false)
    })

    test("rejects a numeric trajectory_id (ids are strings, not numbers)", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, trajectory_id: 123456789 })).toBe(false)
    })

    test("rejects unknown properties", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...base, injected: "x" })).toBe(false)
    })
  })

  describe("the string-id rule holds across the join-key schemas", () => {
    test("trajectory rejects a numeric trajectory_id", () => {
      const validate = validatorFor("trajectory")
      expect(validate({ ...VALID.trajectory, trajectory_id: 123456789 })).toBe(false)
    })

    test("task-spec rejects a numeric task_id", () => {
      const validate = validatorFor("task-spec")
      expect(validate({ ...VALID["task-spec"], task_id: 123456789 })).toBe(false)
    })
  })

  describe("timestamps are integer-nanosecond digit strings", () => {
    test("reward-record rejects a non-numeric gradedAt (RFC 3339 is not the canonical form)", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...VALID["reward-record"], gradedAt: "2026-01-02T03:04:05Z" })).toBe(false)
    })

    test("trajectory rejects a non-numeric createdAt", () => {
      const validate = validatorFor("trajectory")
      expect(validate({ ...VALID.trajectory, createdAt: "not-a-time" })).toBe(false)
    })

    test("reward-record rejects a leading-zero gradedAt (non-canonical — JCS byte-parity)", () => {
      const validate = validatorFor("reward-record")
      expect(validate({ ...VALID["reward-record"], gradedAt: "007" })).toBe(false)
    })
  })

  describe("task-spec tool enum is terraform | cdk", () => {
    test("accepts cdk", () => {
      const validate = validatorFor("task-spec")
      expect(validate({ ...VALID["task-spec"], tool: "cdk" })).toBe(true)
    })

    test("rejects cloudformation (the read substrate, not an authoring tool)", () => {
      const validate = validatorFor("task-spec")
      expect(validate({ ...VALID["task-spec"], tool: "cloudformation" })).toBe(false)
    })
  })

  describe("diff-ir change / propertyDiffs consistency", () => {
    const resource = (over: Record<string, unknown>) => ({
      resources: [
        { address: "AppBucket", type: "AWS::S3::Bucket", change: "unchanged", propertyDiffs: [], ...over },
      ],
    })

    test("a modified resource carries at least one propertyDiff", () => {
      const validate = validatorFor("diff-ir")
      expect(
        validate(
          resource({
            change: "modified",
            propertyDiffs: [
              { path: "VersioningConfiguration.Status", expected: "Enabled", actual: "Suspended" },
            ],
          }),
        ),
      ).toBe(true)
    })

    test("rejects a modified resource with no propertyDiffs", () => {
      const validate = validatorFor("diff-ir")
      expect(validate(resource({ change: "modified", propertyDiffs: [] }))).toBe(false)
    })

    test("rejects an unchanged resource that carries propertyDiffs", () => {
      const validate = validatorFor("diff-ir")
      expect(
        validate(resource({ change: "unchanged", propertyDiffs: [{ path: "X", expected: 1, actual: 2 }] })),
      ).toBe(false)
    })

    test("rejects a propertyDiff carrying neither expected nor actual", () => {
      const validate = validatorFor("diff-ir")
      expect(validate(resource({ change: "modified", propertyDiffs: [{ path: "X" }] }))).toBe(false)
    })
  })
})
