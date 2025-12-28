"""
Adapters for converting common data structures to Sentinel protocols.

These adapters make it easy to integrate existing data formats with
Sentinel's protocol-based interfaces.
"""

from typing import Any, Dict, List

from sentinel.core.interfaces import EvidenceSource


class GitHubBundleEvidenceSource:
    """
    Adapter that converts a GitHub bundle dict to EvidenceSource protocol.

    This allows existing GitHub bundle data to be used with the new
    EvidenceSource abstraction.
    """

    def __init__(self, bundle: Dict[str, Any]):
        """
        Initialize with a GitHub bundle.

        Args:
            bundle: GitHub bundle dict with 'issues' and 'milestone' keys
        """
        self.bundle = bundle

    def get_evidence_items(self) -> List[Dict[str, Any]]:
        """Convert GitHub bundle to evidence items."""
        evidence_items = []

        # Add issues as evidence
        for issue in self.bundle.get("issues", []):
            text = f"{issue.get('title', '')} {issue.get('body', '')}"
            if text.strip():
                evidence_items.append(
                    {
                        "text": text,
                        "source_ref": f"issue:{issue.get('number')}",
                        "source_type": "issue",
                    }
                )

        # Add milestone description as evidence
        milestone = self.bundle.get("milestone", {})
        if milestone.get("description"):
            evidence_items.append(
                {
                    "text": milestone["description"],
                    "source_ref": f"milestone:{milestone.get('number')}",
                    "source_type": "milestone",
                }
            )

        return evidence_items

