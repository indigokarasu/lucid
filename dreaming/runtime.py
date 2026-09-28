"""Runtime helpers for principal-scoped Lucid Dreaming."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .kernel import DreamDomain, DreamKernel, JsonNamespaceStore


@dataclass(frozen=True)
class DreamScope:
    hermes_home: Path
    profile_id: str
    principal_id: str

    @classmethod
    def from_values(
        cls,
        *,
        hermes_home: str | os.PathLike[str] | None = None,
        profile_id: str,
        principal_id: str,
    ) -> "DreamScope":
        home = Path(hermes_home or os.environ.get("HERMES_HOME") or "~/.hermes").expanduser()
        profile = str(profile_id or "").strip()
        principal = str(principal_id or "").strip()
        if not profile:
            raise ValueError("profile_id is required")
        if not principal:
            raise ValueError("principal_id is required")
        if "/" in profile or ".." in profile or "/" in principal or ".." in principal:
            raise ValueError("profile_id/principal_id must be simple identifiers")
        return cls(home.resolve(), profile, principal)

    @property
    def state_root(self) -> Path:
        return (
            self.hermes_home
            / "commons"
            / "data"
            / "dreaming"
            / "profiles"
            / self.profile_id
            / "principals"
            / self.principal_id
        )

    def kernel(self, domain: DreamDomain | str) -> DreamKernel:
        return DreamKernel(
            domain,
            JsonNamespaceStore(
                self.state_root,
                profile_id=self.profile_id,
                principal_id=self.principal_id,
            ),
        )
