"""Shared Dreaming kernel.

The legacy Lucid journal curator remains available during migration, but new
Dreaming code lives here.  Relationship and self evolution share machinery,
never state.
"""

from .kernel import Candidate, DreamDomain, DreamKernel, EvidenceRef, JsonNamespaceStore, PromotionResult

__all__ = [
    "Candidate",
    "DreamDomain",
    "DreamKernel",
    "EvidenceRef",
    "JsonNamespaceStore",
    "PromotionResult",
]
