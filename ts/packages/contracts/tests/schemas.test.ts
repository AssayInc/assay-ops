import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import Ajv2020, { type AnySchemaObject } from "ajv/dist/2020"

// The contract schemas are the neutral source of truth at the repo root (contracts/schemas),
// codegen'd to both lanes in E1-2 (#27). This test file sits at ts/packages/contracts/tests —
// four levels below the repo root.
const SCHEMA_DIR = join(import.meta.dir, "../../../../contracts/schemas")

const SCHEMA_NAMES = ["reward-record", "trajectory", "diff-ir", "task-spec"] as const
type SchemaName = (typeof SCHEMA_NAMES)[number]

function loadSchema(name: SchemaName): AnySchemaObject {
  return JSON.parse(readFileSync(join(SCHEMA_DIR, `${name}.schema.json`), "utf8")) as AnySchemaObject
}

function validatorFor(name: SchemaName) {
  return new Ajv2020({ allErrors: true }).compile(loadSchema(name))
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
    gradedAt: "2026-06-21T12:00:00Z",
    nonce: "5f4dcc3b5aa765d61d8327deb882cf99",
  },
  trajectory: {
    trajectory_id: "traj-01J9Z3K8QmR2",
    task_id: "task-s3-versioning-001",
    createdAt: "2026-06-21T12:00:00Z",
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
  describe("each is a valid Draft 2020-12 schema", () => {
    for (const name of SCHEMA_NAMES) {
      test(name, () => {
        const schema = loadSchema(name)
        expect(schema.$schema).toBe("https://json-schema.org/draft/2020-12/schema")
        expect(typeof schema.$id).toBe("string")
        expect(schema.additionalProperties).toBe(false)
        expect(() => new Ajv2020({ allErrors: true }).compile(schema)).not.toThrow()
      })
    }
  })

  describe("a well-formed instance validates", () => {
    for (const name of SCHEMA_NAMES) {
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
})
