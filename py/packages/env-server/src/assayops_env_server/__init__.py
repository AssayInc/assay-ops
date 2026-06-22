"""AssayOps OpenEnv-native Python env-server (E17-S1 spike, #114).

This package is the **A-side** (agent-reachable) env-server surface only. Per the non-waivable
reward-boundary invariant (DECISIONS.md §8 + I5), nothing here computes the graded reward: the
environment's ``step()`` reward is a zero shaping signal, and the graded ``reward in {0, 1}`` is
delivered out-of-band by the account-B verifier/ledger, joined by ``trajectory_id``.
"""
