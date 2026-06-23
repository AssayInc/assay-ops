// The contract types are generated from contracts/schemas/*.schema.json by `just codegen` (quicktype) —
// see docs/ARCHITECTURE.md. This file is the package's public entry point; src/generated.ts is the
// generated source (carved out of Biome lint; tsc still typechecks it). Regenerate with `just codegen`.
export * from "./generated"
// JCS canonicalization for the TS consumer/verify side of the contract spine (DECISIONS.md I3).
export * from "./jcs"
