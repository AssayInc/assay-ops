import { test, expect } from "bun:test";
import { CreateBucketCommand, S3Client } from "@aws-sdk/client-s3";
import { CloudControlClient, GetResourceCommand } from "@aws-sdk/client-cloudcontrol";

// Cost-free LocalStack dev loop: no real AWS, static test credentials, localhost gateway.
const endpoint = process.env.LOCALSTACK_ENDPOINT ?? "http://localhost:4566";
const region = "us-east-1";
const credentials = { accessKeyId: "test", secretAccessKey: "test" };
const bucketName = "assayops-smoke-bucket";

// Cloud Control GetResource can briefly fail while LocalStack warms the service after the gateway
// reports healthy; retry a few times so a cold CI start does not flake the smoke.
async function getResourceWithRetry(
  client: CloudControlClient,
  input: { TypeName: string; Identifier: string },
  attempts = 6,
) {
  let lastError: unknown;
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      return await client.send(new GetResourceCommand(input));
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
    const s3 = new S3Client({ endpoint, region, credentials, forcePathStyle: true });
    try {
      await s3.send(new CreateBucketCommand({ Bucket: bucketName }));
    } catch (error) {
      // Idempotent against a warm stack: a re-owned/existing bucket is fine, anything else is real.
      const name = error instanceof Error ? error.name : "";
      if (name !== "BucketAlreadyOwnedByYou" && name !== "BucketAlreadyExists") {
        throw error;
      }
    }

    const cloudControl = new CloudControlClient({ endpoint, region, credentials });
    const { ResourceDescription } = await getResourceWithRetry(cloudControl, {
      TypeName: "AWS::S3::Bucket",
      Identifier: bucketName,
    });

    expect(ResourceDescription?.Identifier).toBe(bucketName);
    const properties = JSON.parse(ResourceDescription?.Properties ?? "{}") as {
      BucketName?: string;
    };
    expect(properties.BucketName).toBe(bucketName);
  },
  30_000,
);
