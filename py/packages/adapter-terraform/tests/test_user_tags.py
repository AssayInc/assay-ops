"""User tags are intent the golden may assert -- kept (sorted); only the bridge tag is stripped."""

from __future__ import annotations

from factories import s3_read, s3_registry

from assayops_adapter_terraform import normalize


def test_user_tags_are_preserved_sorted_with_only_the_bridge_tag_stripped() -> None:
    read = s3_read("primary", tags={"team": "infra", "env": "prod"}, BucketName="b")
    [resource] = normalize([read], s3_registry()).resources
    assert resource.properties == {
        "BucketName": "b",
        "Tags": [{"Key": "env", "Value": "prod"}, {"Key": "team", "Value": "infra"}],
    }
