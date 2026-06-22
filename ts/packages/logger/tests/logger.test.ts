import { expect, test } from "bun:test"
import { DEFAULT_REDACT_PATHS, createLoggerOptions, resolveLogLevel } from "../src"

test("resolveLogLevel accepts supported levels and falls back to info", () => {
  expect(resolveLogLevel("debug")).toBe("debug")
  expect(resolveLogLevel("not-a-level")).toBe("info")
  expect(resolveLogLevel(undefined)).toBe("info")
})

test("createLoggerOptions merges default and custom redaction paths", () => {
  const options = createLoggerOptions({
    level: "warn",
    name: "assayops-test",
    pretty: false,
    redact: ["metadata.clientSecret"],
  })

  expect(options.level).toBe("warn")
  expect(options.name).toBe("assayops-test")
  expect(options.redact).toEqual({
    paths: [...DEFAULT_REDACT_PATHS, "metadata.clientSecret"],
    censor: "[redacted]",
  })
})

test("DEFAULT_REDACT_PATHS covers the AWS credential fields", () => {
  expect(DEFAULT_REDACT_PATHS).toContain("accessKeyId")
  expect(DEFAULT_REDACT_PATHS).toContain("secretAccessKey")
  expect(DEFAULT_REDACT_PATHS).toContain("sessionToken")
})
