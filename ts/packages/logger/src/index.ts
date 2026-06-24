// The TypeScript-lane structured logger — scoped to the consumer/web surface (assay-web, dashboards,
// npm consumers). The proof-critical Python core (env-server / verifier / reward ledger) uses the
// structlog mirror `assayops_logger`; both lanes share the SECRET_KEYS redaction contract, kept in
// lockstep by a Python parity test.
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

const SECRET_KEYS = [
  "password",
  "secret",
  "token",
  "accessToken",
  "refreshToken",
  "sessionToken",
  "apiKey",
  "accessKeyId",
  "secretAccessKey",
  "clientSecret",
  "privateKey",
  "authorization",
  "cookie",
] as const

// pino's built-in `redact` (fast-redact): path-based, single-level `*` wildcard, `[*]` for arrays, bracket
// notation for hyphenated keys. Redaction runs at serialization, so it also covers base + child bindings
// and does not flatten Error objects (a hand-rolled formatter does both). Paths are case-sensitive and
// must be init-time constants — never user input (fast-redact syntax-checks them in a VM; see the official
// pino redaction docs). This is defense-in-depth for the credential shapes the verifier and ledger touch
// (AWS creds, KMS material, auth headers) at the common nesting; pino's path model does NOT cover arbitrary
// depth or arrays-of-credentials, so the primary rule remains: don't log secrets.
export const DEFAULT_REDACT_PATHS: readonly string[] = [
  ...SECRET_KEYS.flatMap((key) => [key, `*.${key}`]),
  "credentials.accessKeyId",
  "credentials.secretAccessKey",
  "credentials.sessionToken",
  "*.credentials.accessKeyId",
  "*.credentials.secretAccessKey",
  "*.credentials.sessionToken",
  "headers.authorization",
  "headers.cookie",
  'headers["x-api-key"]',
  'headers["set-cookie"]',
  "*.headers.authorization",
  "*.headers.cookie",
  '*.headers["x-api-key"]',
  '*.headers["set-cookie"]',
]

export interface CreateLoggerOptions {
  bindings?: Bindings
  level?: LevelWithSilent
  name?: string
  pretty?: boolean
  // Additional fast-redact paths. Init-time constants only — never user input (see DEFAULT_REDACT_PATHS).
  redactPaths?: readonly string[]
}

export function createLogger(options: CreateLoggerOptions = {}): Logger {
  return pino(createLoggerOptions(options))
}

export function createLoggerOptions({
  bindings,
  level,
  name,
  pretty = process.env.LOG_PRETTY === "true",
  redactPaths = [],
}: CreateLoggerOptions = {}): LoggerOptions {
  // Never pretty-print in production, even if a caller passes pretty: true.
  const prettyEnabled = pretty && process.env.NODE_ENV !== "production"
  return {
    // Only override pino's default base (pid + hostname) when the caller supplies bindings; otherwise
    // keep pid/hostname so logs stay traceable.
    ...(bindings ? { base: bindings } : {}),
    level: level ?? resolveLogLevel(process.env.LOG_LEVEL),
    name,
    redact: {
      paths: [...DEFAULT_REDACT_PATHS, ...redactPaths],
      censor: "[redacted]",
    },
    serializers: { err: pino.stdSerializers.err },
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
