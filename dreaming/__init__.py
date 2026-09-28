"""Lucid Dreaming.

Lucid is the canonical home of OCAS Dreaming. User and self domains share
orchestration and gating machinery but never state or promotion authority.
"""

from .kernel import Candidate, DreamDomain, DreamKernel, EvidenceRef, JsonNamespaceStore, PromotionResult
from .runtime import DreamScope
from .self import SelfDreamRunner
from .user import UserDreamRunner

__all__ = [
    "Candidate",
    "DreamDomain",
    "DreamKernel",
    "EvidenceRef",
    "JsonNamespaceStore",
    "PromotionResult",
    "DreamScope",
    "SelfDreamRunner",
    "UserDreamRunner",
]
