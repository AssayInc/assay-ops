import { expect, test } from "bun:test"
import { PLACEHOLDER } from "../src/index"

test("contracts package is wired", () => {
  expect(PLACEHOLDER).toBe("assayops-contracts")
})
