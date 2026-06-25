"""Determinism: two reads of one correct deploy -> the same IR (else a flaky reward)."""

from __future__ import annotations

from factories import ADDRESS_TAG, s3_read, s3_registry, tag

from assayops_adapter_terraform import DeployedResourceRead, normalize


def test_resource_order_does_not_change_the_normalized_state() -> None:
    a = s3_read("alpha", identifier="b1", BucketName="a")
    b = s3_read("beta", identifier="b2", BucketName="b")
    assert normalize([a, b], s3_registry()) == normalize([b, a], s3_registry())


def test_user_tag_order_does_not_change_the_normalized_state() -> None:
    forward = s3_read("primary", tags={"env": "prod", "team": "infra"})
    reverse = DeployedResourceRead(
        type_name="AWS::S3::Bucket",
        identifier="b",
        properties={
            "Tags": [tag("team", "infra"), tag("env", "prod"), tag(ADDRESS_TAG, "primary")]
        },
    )
    assert normalize([forward], s3_registry()) == normalize([reverse], s3_registry())


def test_two_reads_of_the_same_correct_deploy_produce_the_same_ir() -> None:
    # Different physical id + server-filled attrs -> identical IR (normalization is complete).
    read_one = s3_read(
        "primary",
        identifier="assayops-aaaa",
        BucketName="assayops-shared",
        Arn="arn:aws:s3:::assayops-shared",
        DomainName="assayops-shared.s3.amazonaws.com",
        VersioningConfiguration={"Status": "Enabled"},
        tags={"env": "prod"},
    )
    read_two = s3_read(
        "primary",
        identifier="assayops-bbbb",
        BucketName="assayops-shared",
        Arn="arn:aws:s3:::a-different-arn",
        DomainName="a-different-domain.s3.amazonaws.com",
        VersioningConfiguration={"Status": "Enabled"},
        tags={"env": "prod"},
    )
    assert normalize([read_one], s3_registry()) == normalize([read_two], s3_registry())
