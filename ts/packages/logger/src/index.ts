import pino from "pino"
import type { Bindings, LevelWithSilent, Logger, LoggerOptions } from "pino"

export const LOG_LEVELS = [
  "fatal",
  "error",
  "warn",
  "info",
  "debug",
  "trace",
  "silent",
] as const satisfies readonly LevelWithSilent[]

// Field names redacted at ANY depth (including inside arrays), matched case-insensitively and ignoring
// `-`/`_` separators — so `secretAccessKey`, `secret_access_key`, and `x-api-key` all match. pino's
// path-based `redact` only matches a fixed depth, which silently leaks nested creds; this repo's verifier
// and ledger touch AWS credentials and KMS signing material across the account-A/B boundary, so the
// redactor walks the whole object. This is defense-in-depth — the primary rule is still: don't log secrets.
export const DEFAULT_REDACT_KEYS = [
  "authorization",
  "cookie",
  "setcookie",
  "password",
  "secret",
  "token",
  "accesstoken",
  "refreshtoken",
  "sessiontoken",
  "apikey",
  "xapikey",
  "accesskeyid",
  "secretaccesskey",
  "clientsecret",
  "privatekey",
] as const

const REDACTED = "[redacted]"

function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/[-_]/g, "")
}

function redactInto(value: unknown, keys: ReadonlySet<string>, seen: WeakSet<object>): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => redactInto(item, keys, seen))
  }
  if (value !== null && typeof value === "object") {
    if (seen.has(value)) {
      return value
    }
    seen.add(value)
    const out: Record<string, unknown> = {}
    for (const [key, child] of Object.entries(value)) {
      out[key] = keys.has(normalizeKey(key)) ? REDACTED : redactInto(child, keys, seen)
    }
    return out
  }
  return value
}

function redactKeySet(extraKeys: readonly string[]): ReadonlySet<string> {
  return new Set([...DEFAULT_REDACT_KEYS, ...extraKeys.map(normalizeKey)])
}

// Deep-redact an arbitrary value by key name (DEFAULT_REDACT_KEYS plus any extras). Returns a redacted
// copy; the input is not mutated. Cycles are left intact (not re-walked).
export function redact(value: unknown, extraKeys: readonly string[] = []): unknown {
  return redactInto(value, redactKeySet(extraKeys), new WeakSet())
}

export interface CreateLoggerOptions {
  bindings?: Bindings
  level?: LevelWithSilent
  name?: string
  pretty?: boolean
  redactKeys?: readonly string[]
}

export function createLogger(options: CreateLoggerOptions = {}): Logger {
  return pino(createLoggerOptions(options))
}

export function createLoggerOptions({
  bindings,
  level,
  name,
  pretty = process.env.LOG_PRETTY === "true",
  redactKeys = [],
}: CreateLoggerOptions = {}): LoggerOptions {
  const keys = redactKeySet(redactKeys)
  // Never pretty-print in production, even if a caller passes pretty: true.
  const prettyEnabled = pretty && process.env.NODE_ENV !== "production"
  return {
    base: bindings,
    level: level ?? resolveLogLevel(process.env.LOG_LEVEL),
    name,
    formatters: {
      log(object) {
        return redactInto(object, keys, new WeakSet()) as Record<string, unknown>
      },
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    transport: prettyEnabled
      ? {
          target: "pino-pretty",
          options: {
            colorize: true,
            ignore: "pid,hostname",
            translateTime: "SYS:standard",
          },
        }
      : undefined,
  }
}

export function createChildLogger(logger: Logger, bindings: Bindings): Logger {
  return logger.child(bindings)
}

export function resolveLogLevel(value: string | undefined): LevelWithSilent {
  if (isLogLevel(value)) {
    return value
  }

  return "info"
}

function isLogLevel(value: string | undefined): value is LevelWithSilent {
  return LOG_LEVELS.some((level) => level === value)
}
