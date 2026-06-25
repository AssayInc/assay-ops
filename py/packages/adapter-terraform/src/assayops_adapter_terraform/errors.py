"""The adapter's fail-closed exception family (DECISIONS.md T1 / §5 vector #15 / §8).

The adapter raises rather than emit a ``NormalizedState`` it cannot vouch for: a silently-dropped or
mis-addressed resource could grade a wrong deploy as in-sync. Every failure is an ``AdapterError``
(a ``ValueError``), so the verifier skeleton (#30) catches one family and quarantines the episode.
"""

from __future__ import annotations


class AdapterError(ValueError):
    """Base: the Terraform adapter could not safely normalize a read, so it fails closed."""


class UnsupportedResourceTypeError(AdapterError):
    """A read whose CloudFormation type has no registered bridge (the #80 read-coverage matrix).

    Unsupported types are quarantined at corpus-authoring time; this is the runtime backstop.
    """


class UnreadableResourceError(AdapterError):
    """An ``UnreadableResource`` in the input -- a per-record coverage gap, never a silent reward.

    The global closed-world ``deployed set == golden set`` check is the read harness's job (#141).
    """


class AddressBridgeError(AdapterError):
    """The ``assayops:address`` bridge could not be resolved from a read's tags.

    Fires on a missing / duplicate / malformed address, a stray reserved ``assayops:*`` tag, or a
    wrong-shape tag property. The tag value is untrusted, so it is validated, never trusted.
    """


class DuplicateAddressError(AdapterError):
    """Two reads resolve to the same logical address -- they collide in the diff's address map."""
