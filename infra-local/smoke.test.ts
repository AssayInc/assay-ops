import { test, expect } from "bun:test";
import { CreateBucketCommand, S3Client } from "@aws-sdk/client-s3";
import { CloudControlClient, GetResourceCommand } from "@aws-sdk/client-cloudcontrol";

// Cost-free LocalStack dev loop: no real AWS, static test credentials, localhost gateway.
const endpoint = process.env.LOCALSTACK_ENDPOINT ?? "http://localhost:4566";
const region = "us-east-1";
const credentials = { accessKeyId: "test", secretAccessKey: "test" };
const bucketName = "assayops-smoke-bucket";

// Drive retry timing from this script, not the SDK: one attempt + a bounded socket timeout, so a hung
// (vs refused) LocalStack cannot stack the SDK's default 3 retries against the test budget.
const clientConfig = {
  endpoint,
  region,
  credentials,
  maxAttempts: 1,
  requestHandler: { requestTimeout: 5000 },
};

// LocalStack can briefly fail while it warms a service after the gateway reports healthy; retry the
// whole step a few times so a cold CI start does not flake. Always rethrows the last error, so a
// genuine failure still fails the test (never a false pass).
async function withRetry<T>(operation: () => Promise<T>, attempts = 6): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (attempt < attempts - 1) {
        await new Promise((resolve) => {
          setTimeout(resolve, 1000);
        });
      }
    }
  }
  throw lastError;
}

// Seeds a known S3 bucket, then reads it back read-only via Cloud Control GetResource: the minimal
// seed of the E2 verifier's deployed-state read path (DECISIONS.md section 1), not the verifier itself.
test(
  "Cloud Control GetResource reads a deployed S3 bucket from LocalStack",
  async () => {
    const s3 = new S3Client({ ...clientConfig, forcePathStyle: true });
    await withRetry(async () => {
      try {
        await s3.send(new CreateBucketCommand({ Bucket: bucketName }));
      } catch (error) {
        // Idempotent against a warm stack: a re-owned/existing bucket is fine, anything else retries.
        const name = error instanceof Error ? error.name : "";
        if (name !== "BucketAlreadyOwnedByYou" && name !== "BucketAlreadyExists") {
          throw error;
        }
      }
    });

    const cloudControl = new CloudControlClient(clientConfig);
    const { ResourceDescription } = await withRetry(() =>
      cloudControl.send(
        new GetResourceCommand({ TypeName: "AWS::S3::Bucket", Identifier: bucketName }),
      ),
    );

    expect(ResourceDescription?.Identifier).toBe(bucketName);
    const properties = JSON.parse(ResourceDescription?.Properties ?? "{}") as {
      BucketName?: string;
    };
    expect(properties.BucketName).toBe(bucketName);
  },
  30_000,
);
