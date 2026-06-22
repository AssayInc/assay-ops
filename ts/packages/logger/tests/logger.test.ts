import { expect, test } from "bun:test"
import pino from "pino"
import { DEFAULT_REDACT_KEYS, createLoggerOptions, redact, resolveLogLevel } from "../src"

test("resolveLogLevel accepts supported levels and falls back to info", () => {
  expect(resolveLogLevel("debug")).toBe("debug")
  expect(resolveLogLevel("not-a-level")).toBe("info")
  expect(resolveLogLevel(undefined)).toBe("info")
})

test("createLoggerOptions sets level, name, and a redacting log formatter", () => {
  const options = createLoggerOptions({ level: "warn", name: "assayops-test" })
  expect(options.level).toBe("warn")
  expect(options.name).toBe("assayops-test")
  expect(typeof options.formatters?.log).toBe("function")
})

test("DEFAULT_REDACT_KEYS covers the high-value credential names", () => {
  expect(DEFAULT_REDACT_KEYS).toContain("secretaccesskey")
  expect(DEFAULT_REDACT_KEYS).toContain("privatekey")
  expect(DEFAULT_REDACT_KEYS).toContain("authorization")
})

test("redact scrubs secret keys at any depth, inside arrays, across name variants", () => {
  const out = JSON.stringify(
    redact({
      config: { credentials: { accessKeyId: "AKIA_LEAK", secretAccessKey: "SAK_LEAK" } },
      req: { headers: { authorization: "Bearer TOK_LEAK", "x-api-key": "XAK_LEAK", cookie: "CK_LEAK" } },
      results: [{ sessionToken: "STS_LEAK" }],
      private_key: "PK_LEAK",
      keep: "visible",
    }),
  )

  for (const leaked of [
    "AKIA_LEAK",
    "SAK_LEAK",
    "Bearer TOK_LEAK",
    "XAK_LEAK",
    "CK_LEAK",
    "STS_LEAK",
    "PK_LEAK",
  ]) {
    expect(out).not.toContain(leaked)
  }
  expect(out).toContain("[redacted]")
  expect(out).toContain("visible")
})

test("redact accepts extra key names", () => {
  const out = JSON.stringify(redact({ deploymentPin: "PIN_LEAK" }, ["deploymentPin"]))
  expect(out).not.toContain("PIN_LEAK")
  expect(out).toContain("[redacted]")
})

test("a real pino logger redacts nested credentials in its emitted output", () => {
  const lines: string[] = []
  const logger = pino(createLoggerOptions({ level: "info" }), {
    write: (line: string) => {
      lines.push(line)
    },
  })

  logger.info(
    { req: { headers: { authorization: "Bearer REAL_LEAK" } }, creds: [{ secretAccessKey: "ARR_LEAK" }] },
    "request",
  )

  const emitted = lines.join("")
  expect(emitted).not.toContain("Bearer REAL_LEAK")
  expect(emitted).not.toContain("ARR_LEAK")
  expect(emitted).toContain("[redacted]")
})
