"""License Compatibility Enforcement Policy.

As specified in SPEC §10.1 and Invariant 10:
- "Licenses are enforced, not recorded. An asset whose license forbids the intended use is rejected by a gate."
- CC-BY-NC and CC-BY-ND are strictly blocked.
- PD, CC0, CC-BY, CC-BY-SA, Pexels/Pixabay terms are permitted with requirements recorded.
"""

from typing import Any

from atlas.platform.errors import AiImageUnapprovedError, LicenseIncompatibleError


class LicensePolicy:
    """Enforces license rules and approval requirements for media assets (Invariants 9 & 10)."""

    # Explicitly allowed licenses
    ALLOWED_LICENSES = {
        "public domain",
        "pd",
        "pd-mark",
        "cc0",
        "cc0-1.0",
        "cc-by",
        "cc-by-2.0",
        "cc-by-3.0",
        "cc-by-4.0",
        "cc-by-sa",
        "cc-by-sa-3.0",
        "cc-by-sa-4.0",
        "pixabay",
        "pexels",
        "freesound cc0",
        "freesound cc-by",
    }

    # Explicitly blocked license terms
    BLOCKED_TERMS = ["nc", "noncommercial", "non-commercial", "nd", "noderivs", "no-derivatives"]

    @classmethod
    def validate_asset_license(
        cls, asset_id: str, license_id: str, _metadata: dict[str, Any] | None = None
    ) -> bool:
        """Validate if license is compatible with video compilation and distribution."""
        norm_license = license_id.strip().lower()

        # 1. Check for blocked terms (Non-commercial / No-derivatives)
        for term in cls.BLOCKED_TERMS:
            if term in norm_license:
                raise LicenseIncompatibleError(
                    asset_id,
                    license_id,
                    f"License contains forbidden restriction '{term}' (SPEC §10.1)",
                )

        # 2. Check allowlist
        if norm_license not in cls.ALLOWED_LICENSES and not norm_license.startswith("cc-by"):
            raise LicenseIncompatibleError(
                asset_id,
                license_id,
                "License is unknown or unverified; unresolvable licenses are hard blockers",
            )

        return True

    @classmethod
    def validate_ai_image_approval(cls, asset_id: str, is_human_approved: bool) -> bool:
        """Enforce Invariant 9: AI-generated imagery always requires explicit human approval."""
        if not is_human_approved:
            raise AiImageUnapprovedError(asset_id)
        return True
