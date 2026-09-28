"""Helpers for feeding Autobio observations into SELF Dreaming.

This adapter does not write SOUL. Autobio remains the sole promotion authority
for Indigo identity; the current boundary kernel stages and gates self-reflection state.
"""

from __future__ import annotations

from .kernel import DreamDomain, DreamKernel, EvidenceRef


def propose_self_observation(
    kernel: DreamKernel,
    *,
    observation_id: str,
    text: str,
    confidence: float = 0.7,
):
    if kernel.domain is not DreamDomain.SELF:
        raise ValueError("Autobio observations may only seed self Dreaming")
    if not observation_id:
        raise ValueError("observation_id is required")
    return kernel.propose(
        kind="autobio_observation",
        text=text,
        confidence=confidence,
        evidence=[EvidenceRef(kind="autobio_observation", ref_id=observation_id)],
        source="ocas-autobio",
    )
