import { expect, test } from "bun:test"
import pino from "pino"
import { once, sink } from "pino-test"
import { DEFAULT_REDACT_PATHS, createLoggerOptions, resolveLogLevel } from "../src"

test("resolveLogLevel accepts supported levels and falls back to info", () => {
  expect(resolveLogLevel("debug")).toBe("debug")
  expect(resolveLogLevel("not-a-level")).toBe("info")
  expect(resolveLogLevel(undefined)).toBe("info")
})

test("createLoggerOptions sets level, name, and the redact censor", () => {
  const options = createLoggerOptions({ level: "warn", name: "assayops-test" })
  expect(options.level).toBe("warn")
  expect(options.name).toBe("assayops-test")
  expect(options.redact).toMatchObject({ censor: "[redacted]" })
})

test("DEFAULT_REDACT_PATHS covers the high-value credential paths", () => {
  expect(DEFAULT_REDACT_PATHS).toContain("secretAccessKey")
  expect(DEFAULT_REDACT_PATHS).toContain("*.secretAccessKey")
  expect(DEFAULT_REDACT_PATHS).toContain("*.credentials.secretAccessKey")
  expect(DEFAULT_REDACT_PATHS).toContain("privateKey")
})

test("redacts top-level, nested, AWS-credential, and header secrets", async () => {
  const stream = sink()
  const logger = pino(createLoggerOptions({ level: "info" }), stream)

  logger.info(
    {
      password: "secret",
      config: { secretAccessKey: "sak1", credentials: { secretAccessKey: "sak2" } },
      req: { headers: { authorization: "Bearer t", "x-api-key": "k" } },
      keep: "visible",
    },
    "msg",
  )

  await once(stream, {
    level: 30,
    msg: "msg",
    password: "[redacted]",
    config: { secretAccessKey: "[redacted]", credentials: { secretAccessKey: "[redacted]" } },
    req: { headers: { authorization: "[redacted]", "x-api-key": "[redacted]" } },
    keep: "visible",
  })
})

test("redacts secrets carried on child-logger bindings", async () => {
  const stream = sink()
  const logger = pino(createLoggerOptions({ level: "info" }), stream)

  logger.child({ authorization: "Bearer c", service: "verifier" }).info("with binding")

  await once(stream, {
    level: 30,
    msg: "with binding",
    authorization: "[redacted]",
    service: "verifier",
  })
})

test("preserves Error message and stack (redaction does not flatten errors)", async () => {
  const stream = sink()
  const logger = pino(createLoggerOptions({ level: "info" }), stream)

  logger.info({ err: new Error("BOOM_MARKER") }, "failed")

  await once(stream, (log: { err?: { message?: string; stack?: string } }) => {
    expect(log.err?.message).toBe("BOOM_MARKER")
    expect(typeof log.err?.stack).toBe("string")
  })
})
