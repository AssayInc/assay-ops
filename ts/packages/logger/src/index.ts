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

// Trust-boundary defense: never log credentials. Covers the AWS creds the verifier and ledger touch
// across the account-A/B boundary, plus common auth fields — at the root and one level deep.
export const DEFAULT_REDACT_PATHS = [
  "authorization",
  "cookie",
  "password",
  "secret",
  "token",
  "apiKey",
  "accessKeyId",
  "secretAccessKey",
  "sessionToken",
  "*.authorization",
  "*.cookie",
  "*.password",
  "*.secret",
  "*.token",
  "*.apiKey",
  "*.accessKeyId",
  "*.secretAccessKey",
  "*.sessionToken",
] as const

export interface CreateLoggerOptions {
  bindings?: Bindings
  level?: LevelWithSilent
  name?: string
  pretty?: boolean
  redact?: readonly string[]
}

export function createLogger(options: CreateLoggerOptions = {}): Logger {
  return pino(createLoggerOptions(options))
}

export function createLoggerOptions({
  bindings,
  level,
  name,
  pretty = process.env.LOG_PRETTY === "true" && process.env.NODE_ENV !== "production",
  redact = [],
}: CreateLoggerOptions = {}): LoggerOptions {
  return {
    base: bindings,
    level: level ?? resolveLogLevel(process.env.LOG_LEVEL),
    name,
    redact: {
      paths: [...DEFAULT_REDACT_PATHS, ...redact],
      censor: "[redacted]",
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    transport: pretty
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
