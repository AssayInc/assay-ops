import { expect, test } from "bun:test"
import pino from "pino"
import { DEFAULT_REDACT_PATHS, createLoggerOptions, resolveLogLevel } from "../src"

function emit(payload: Record<string, unknown>, msg = "test"): string {
  const lines: string[] = []
  const logger = pino(createLoggerOptions({ level: "info" }), {
    write: (line: string) => {
      lines.push(line)
    },
  })
  logger.info(payload, msg)
  return lines.join("")
}

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

test("redacts top-level, nested, AWS-credential, and header secrets in real output", () => {
  const out = emit({
    password: "PW_LEAK",
    config: { secretAccessKey: "SAK1_LEAK", credentials: { secretAccessKey: "SAK2_LEAK" } },
    req: { headers: { authorization: "Bearer TOK_LEAK", "x-api-key": "XAK_LEAK" } },
    keep: "visible",
  })
  for (const leaked of ["PW_LEAK", "SAK1_LEAK", "SAK2_LEAK", "Bearer TOK_LEAK", "XAK_LEAK"]) {
    expect(out).not.toContain(leaked)
  }
  expect(out).toContain("[redacted]")
  expect(out).toContain("visible")
})

test("redacts secrets carried on child-logger bindings (pino redact covers bindings)", () => {
  const lines: string[] = []
  const base = pino(createLoggerOptions({ level: "info" }), {
    write: (line: string) => {
      lines.push(line)
    },
  })
  base.child({ authorization: "Bearer CHILD_LEAK", service: "verifier" }).info("with binding")
  const out = lines.join("")
  expect(out).not.toContain("Bearer CHILD_LEAK")
  expect(out).toContain("[redacted]")
  expect(out).toContain("verifier")
})

test("preserves Error message and stack (redaction does not flatten errors)", () => {
  const out = emit({ err: new Error("BOOM_MARKER") })
  expect(out).toContain("BOOM_MARKER")
  expect(out).toContain("stack")
})
