"""Happy-path normalization: a tagged Cloud Control read -> NormalizedState(DEPLOYED_READ)."""

from __future__ import annotations

from assayops_diff_ir import Provenance
from factories import s3_read, s3_registry

from assayops_adapter_terraform import normalize


def test_bridges_the_assayops_address_tag_to_the_logical_address() -> None:
    # The physical Cloud Control identifier is never the address; the `assayops:address` tag is.
    state = normalize([s3_read("primary_bucket")], s3_registry())
    assert [r.address for r in state.resources] == ["primary_bucket"]
    assert state.resources[0].type == "AWS::S3::Bucket"


def test_provenance_is_a_deployed_read() -> None:
    state = normalize([s3_read("primary_bucket")], s3_registry())
    assert state.provenance is Provenance.DEPLOYED_READ


def test_drops_server_filled_read_only_properties() -> None:
    # Arn/DomainName/... are AWS-computed and vary across deploys -> dropped (else a flaky reward).
    read = s3_read(
        "primary_bucket",
        BucketName="assayops-a1b2c3d4",
        Arn="arn:aws:s3:::assayops-a1b2c3d4",
        DomainName="assayops-a1b2c3d4.s3.amazonaws.com",
        RegionalDomainName="assayops-a1b2c3d4.s3.us-east-1.amazonaws.com",
    )
    [resource] = normalize([read], s3_registry()).resources
    assert resource.properties == {"BucketName": "assayops-a1b2c3d4"}


def test_keeps_intent_bearing_properties() -> None:
    read = s3_read(
        "primary_bucket",
        BucketName="assayops-a1b2c3d4",
        VersioningConfiguration={"Status": "Enabled"},
    )
    [resource] = normalize([read], s3_registry()).resources
    assert resource.properties == {
        "BucketName": "assayops-a1b2c3d4",
        "VersioningConfiguration": {"Status": "Enabled"},
    }


def test_the_bridge_tag_is_stripped_from_normalized_properties() -> None:
    read = s3_read("primary_bucket", BucketName="assayops-a1b2c3d4")
    [resource] = normalize([read], s3_registry()).resources
    assert "Tags" not in resource.properties
