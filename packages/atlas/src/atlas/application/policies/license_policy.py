"""License Compatibility Enforcement Policy.

As specified in SPEC §10.1 and Invariant 10:
- "Licenses are enforced, not recorded. An asset whose license forbids the intended use is rejected by a gate."
- CC-BY-NC and CC-BY-ND are strictly blocked.
- PD, CC0, CC-BY, CC-BY-SA, Pexels/Pixabay terms are permitted with requirements recorded.

Matching runs on a canonical form of the license identifier, because the two
image adapters do not speak the same dialect: Wikimedia Commons reports
`LicenseShortName` ("CC BY-SA 4.0", "Public domain") and the Internet Archive
reports a `licenseurl` ("https://creativecommons.org/publicdomain/zero/1.0/").
Comparing either against a hyphenated allowlist rejected every validly licensed
asset, and a substring test for "nc" flagged the word "licence" as
non-commercial (defect V-10).
"""

import re
from typing import Any

from atlas.platform.errors import AiImageUnapprovedError, LicenseIncompatibleError

_CC_URL = re.compile(
    r"creativecommons\.org/(?P<kind>licenses|publicdomain)/(?P<code>[a-z0-9-]+)", re.I
)
_SEPARATORS = re.compile(r"[\s_/]+")


def canonicalize_license(license_id: str) -> str:
    """Reduce a license identifier to the hyphenated lower-case form used here.

    `"CC BY-SA 4.0"`, `"cc-by-sa-4.0"` and
    `"https://creativecommons.org/licenses/by-sa/4.0/"` all reduce to
    `"cc-by-sa-4.0"`; `"https://creativecommons.org/publicdomain/zero/1.0/"`
    reduces to `"cc0"`.
    """
    raw = license_id.strip().lower()

    url_match = _CC_URL.search(raw)
    if url_match:
        kind, code = url_match.group("kind"), url_match.group("code")
        if kind == "publicdomain":
            return "cc0" if code == "zero" else "pd-mark"
        version = re.search(r"/(\d+\.\d+)", raw[url_match.end() :])
        return f"cc-{code}" + (f"-{version.group(1)}" if version else "")

    normalized = _SEPARATORS.sub("-", raw).strip("-")
    # "cc by-sa 4.0" arrives as "cc-by-sa-4.0"; "ccby" is not a real spelling.
    return normalized


class LicensePolicy:
    """Enforces license rules and approval requirements for media assets (Invariants 9 & 10)."""

    # Explicitly allowed licenses, in canonical form.
    ALLOWED_LICENSES = {
        "public-domain",
        "public-domain-mark",
        "pd",
        "pd-mark",
        "cc0",
        "cc0-1.0",
        "cc-zero",
        "cc-by",
        "cc-by-2.0",
        "cc-by-3.0",
        "cc-by-4.0",
        "cc-by-sa",
        "cc-by-sa-3.0",
        "cc-by-sa-4.0",
        "pixabay",
        "pexels",
        "freesound-cc0",
        "freesound-cc-by",
    }

    # Blocked restrictions, matched as whole hyphen-delimited tokens so that
    # "licence" is not read as "nc" and "understanding" is not read as "nd".
    BLOCKED_TOKENS = frozenset({"nc", "nd", "noncommercial", "non-commercial", "noderivs"})
    BLOCKED_SUBSTRINGS = ("noncommercial", "non-commercial", "no-derivatives", "noderivs")

    @classmethod
    def validate_asset_license(
        cls, asset_id: str, license_id: str, _metadata: dict[str, Any] | None = None
    ) -> bool:
        """Validate if license is compatible with video compilation and distribution."""
        canonical = canonicalize_license(license_id)
        tokens = set(canonical.split("-"))

        # 1. Check for blocked restrictions (non-commercial / no-derivatives).
        blocked = (tokens & cls.BLOCKED_TOKENS) or {
            term for term in cls.BLOCKED_SUBSTRINGS if term in canonical
        }
        if blocked:
            raise LicenseIncompatibleError(
                asset_id,
                license_id,
                f"License contains forbidden restriction '{sorted(blocked)[0]}' (SPEC §10.1)",
            )

        # 2. Check allowlist. An unresolvable license is a hard blocker: silence
        #    is not permission.
        if canonical not in cls.ALLOWED_LICENSES and not canonical.startswith("cc-by"):
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
