/**
 * Tool-agnostic normalized diff between read-back deployed state and the regenerated golden
 * target. A per-tool adapter (E3) produces this IR; the shared reward core reads it. Reward
 * 1 = zero normalized diff (every resource unchanged).
 */
export interface DiffIR {
    /**
     * One entry per golden/deployed resource, after normalization (canonical order;
     * AWS-assigned ids/timestamps/suffixes dropped).
     */
    resources: Resource[];
}

export interface Resource {
    /**
     * Normalized structural/logical address (never a physical AWS id).
     */
    address: string;
    /**
     * Diff status against the golden.
     */
    change: Change;
    /**
     * Per-property differences (present when change is "modified").
     */
    propertyDiffs?: PropertyDiff[];
    /**
     * Resource type, e.g. AWS::S3::Bucket.
     */
    type: string;
}

/**
 * Diff status against the golden.
 */
export enum Change {
    Added = "added",
    Modified = "modified",
    Removed = "removed",
    Unchanged = "unchanged",
}

export interface PropertyDiff {
    /**
     * Deployed value — any JSON, same caveat as `expected`. Absent when the property is missing
     * from deployed state.
     */
    actual?: any;
    /**
     * Golden value — any JSON. Intentionally unconstrained here; the per-resource value shape
     * and number normalization (including the large-number-as-string rule) are fixed where the
     * diff IR is produced. Absent when the property was added in deployed state.
     */
    expected?: any;
    /**
     * Dotted property path, e.g. VersioningConfiguration.Status.
     */
    path: string;
}

/**
 * The reward record keyed by trajectory_id. This is the canonical payload that is RFC 8785
 * (JCS) canonicalized and KMS-signed in account B; the signature envelope is added by the
 * reward ledger (E4). A buying lab verifies it offline against the public key.
 */
export interface RewardRecord {
    /**
     * Re-grade counter (≤ 2^53−1 to stay JCS-exact). A divergent re-grade appends a new record
     * (a new attempt), never an overwrite.
     */
    attempt: number;
    /**
     * Grading time as integer nanoseconds since the Unix epoch, encoded as a canonical digit
     * string (no leading zeros; ~19 digits exceeds 2^53, so it must be a string). One canonical
     * form — never RFC 3339 — keeps the signed bytes unambiguous.
     */
    gradedAt: string;
    /**
     * Pins which grader/vectors produced this reward.
     */
    graderVersion: string;
    /**
     * Verifier-issued episode nonce; binds the record to this run so a signed reward cannot be
     * replayed.
     */
    nonce: string;
    /**
     * SHA-256 (lowercase hex) of the diff report the reward was read from.
     */
    reportDigest: string;
    /**
     * Execution-grounded reward ∈ {0,1}: binary (zero normalized diff = 1), a finite JCS-safe
     * number. The enum admits only 0 and 1 — rejecting NaN/Infinity and any partial-credit
     * (0.0–1.0) value.
     */
    reward: number;
    /**
     * Join key for the whole system; a string so large opaque ids never lose precision under
     * JCS.
     */
    trajectory_id: string;
}

/**
 * A deploy-graded task definition. The golden target is regenerated reproducibly from
 * (tool, seed); the verifier never grades the agent's submitted config.
 */
export interface TaskSpec {
    /**
     * What the agent must accomplish.
     */
    description: string;
    /**
     * Golden-generation seed; a string so large/opaque seeds never lose precision under JCS.
     */
    seed: string;
    /**
     * Stable task id, referenced by a trajectory's task_id.
     */
    task_id: string;
    /**
     * Short human-readable title.
     */
    title: string;
    /**
     * IaC tool the task is authored against — Terraform (the Phase-1 A-spike engine) or CDK
     * (Phase 2). CloudFormation is the deployed-state read substrate (CDK compiles to it), not
     * an authoring tool.
     */
    tool: Tool;
}

/**
 * IaC tool the task is authored against — Terraform (the Phase-1 A-spike engine) or CDK
 * (Phase 2). CloudFormation is the deployed-state read substrate (CDK compiles to it), not
 * an authoring tool.
 */
export enum Tool {
    Cdk = "cdk",
    Terraform = "terraform",
}

/**
 * An episode's observation/action trace, keyed by trajectory_id. The trainer joins reward
 * records to trajectories on trajectory_id.
 */
export interface Trajectory {
    /**
     * Episode start as integer nanoseconds since the Unix epoch, encoded as a canonical digit
     * string (no leading zeros; same form as the reward record's gradedAt).
     */
    createdAt: string;
    /**
     * Ordered observation/action steps.
     */
    steps: Step[];
    /**
     * The task-spec this episode ran.
     */
    task_id: string;
    /**
     * Join key shared with the reward record; a string so large opaque ids never lose precision
     * under JCS.
     */
    trajectory_id: string;
}

export interface Step {
    /**
     * Agent action taken at this step.
     */
    action: { [key: string]: any };
    /**
     * Zero-based step index (≤ 2^53−1 to stay JCS-exact).
     */
    index: number;
    /**
     * Environment observation at this step.
     */
    observation: { [key: string]: any };
}
