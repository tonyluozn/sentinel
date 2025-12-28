"""Fetch and bundle GitHub milestone data."""

import json
from pathlib import Path
from typing import Dict

from sentinel.config import get_data_dir
from sentinel.trace.schema import EventType, new_event
from sentinel.trace.store_jsonl import JsonlTraceStore
from sentinel.util import slugify

from sentinel.github.cache import FileCache
from sentinel.github.client import GitHubClient


def fetch_repo_milestone_bundle(
    repo: str,
    milestone: str,
    cache: FileCache,
    client: GitHubClient,
    trace_store: JsonlTraceStore,
) -> Dict:
    """Fetch and bundle GitHub milestone data.

    Args:
        repo: Repository in format "owner/repo".
        milestone: Milestone title.
        cache: File cache instance.
        client: GitHub client instance.
        trace_store: Trace store for logging.

    Returns:
        Normalized bundle dict with repo, milestone, and issues.
    """
    # Emit tool_call event
    trace_store.append(
        new_event(
            EventType.TOOL_CALL,
            {
                "tool": "github.fetch",
                "repo": repo,
                "milestone": milestone,
            },
        )
    )

    # Check cache first
    repo_slug = slugify(repo)
    milestone_slug = slugify(milestone)
    cache_key = cache._make_key(repo_slug, milestone_slug, "bundle", {})
    cached = cache.get(cache_key)

    if cached:
        # Emit observation from cache
        trace_store.append(
            new_event(
                EventType.OBSERVATION,
                {
                    "source": "cache",
                    "repo": repo,
                    "milestone": milestone,
                    "issue_count": len(cached.get("issues", [])),
                },
            )
        )
        return cached

    # Fetch from API
    milestones = client.get_milestones(repo)
    milestone_obj = None
    for m in milestones:
        if m["title"] == milestone:
            milestone_obj = m
            break

    if not milestone_obj:
        raise ValueError(f"Milestone '{milestone}' not found in {repo}")

    issues = client.get_issues(repo, milestone)

    # Normalize bundle
    bundle = {
        "repo": {
            "owner": repo.split("/")[0],
            "name": repo.split("/")[1],
            "full_name": repo,
        },
        "milestone": {
            "title": milestone_obj["title"],
            "number": milestone_obj["number"],
            "description": milestone_obj.get("description", ""),
            "state": milestone_obj["state"],
            "created_at": milestone_obj["created_at"],
            "due_on": milestone_obj.get("due_on"),
            "closed_at": milestone_obj.get("closed_at"),
        },
        "issues": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body", ""),
                "state": issue["state"],
                "labels": [label["name"] for label in issue.get("labels", [])],
                "created_at": issue["created_at"],
                "closed_at": issue.get("closed_at"),
                "user": issue.get("user", {}).get("login", ""),
            }
            for issue in issues
            if "pull_request" not in issue  # Exclude PRs unless explicitly requested
        ],
    }

    # Cache bundle
    cache.set(cache_key, bundle)

    # Write to data directory
    data_dir = get_data_dir()
    bundle_path = data_dir / repo_slug / milestone_slug / "bundle.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    # Emit observation event
    label_counts = {}
    for issue in bundle["issues"]:
        for label in issue["labels"]:
            label_counts[label] = label_counts.get(label, 0) + 1

    top_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    trace_store.append(
        new_event(
            EventType.OBSERVATION,
            {
                "source": "api",
                "repo": repo,
                "milestone": milestone,
                "issue_count": len(bundle["issues"]),
                "label_counts": dict(top_labels),
            },
        )
    )

    return bundle
