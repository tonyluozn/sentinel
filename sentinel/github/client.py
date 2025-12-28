"""GitHub API client."""

import os
import time
from typing import Dict, List, Optional

import requests


class GitHubClient:
    """Lightweight GitHub API client with rate limiting."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token. If None, reads from GITHUB_TOKEN env var.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def _check_rate_limit(self):
        """Check rate limit and sleep if needed."""
        response = self.session.get(f"{self.BASE_URL}/rate_limit")
        if response.status_code == 200:
            data = response.json()
            remaining = data.get("resources", {}).get("core", {}).get("remaining", 0)
            if remaining < 10:
                reset_time = data.get("resources", {}).get("core", {}).get("reset", 0)
                sleep_time = max(0, reset_time - time.time() + 1)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make API request with retry logic.

        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            Response object.

        Raises:
            requests.RequestException: On API failure after retries.
        """
        self._check_rate_limit()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 403:
                    # Rate limited, wait and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
        raise requests.RequestException("Failed after retries")

    def get_milestones(self, repo: str) -> List[Dict]:
        """Get milestones for a repository.

        Args:
            repo: Repository in format "owner/repo".

        Returns:
            List of milestone dicts.
        """
        url = f"{self.BASE_URL}/repos/{repo}/milestones"
        response = self._request("GET", url, params={"state": "all"})
        return response.json()

    def get_issues(self, repo: str, milestone: Optional[str] = None) -> List[Dict]:
        """Get issues for a repository.

        Args:
            repo: Repository in format "owner/repo".
            milestone: Milestone title or number. If None, returns all issues.

        Returns:
            List of issue dicts.
        """
        url = f"{self.BASE_URL}/repos/{repo}/issues"
        params = {"state": "all"}
        if milestone:
            # Try to find milestone by title or number
            milestones = self.get_milestones(repo)
            milestone_obj = None
            for m in milestones:
                if m["title"] == milestone or str(m["number"]) == str(milestone):
                    milestone_obj = m
                    break
            if milestone_obj:
                params["milestone"] = milestone_obj["number"]
        response = self._request("GET", url, params=params)
        return response.json()

    def get_issue(self, repo: str, issue_num: int) -> Dict:
        """Get a specific issue.

        Args:
            repo: Repository in format "owner/repo".
            issue_num: Issue number.

        Returns:
            Issue dict.
        """
        url = f"{self.BASE_URL}/repos/{repo}/issues/{issue_num}"
        response = self._request("GET", url)
        return response.json()

    def get_comments(self, repo: str, issue_num: int) -> List[Dict]:
        """Get comments for an issue.

        Args:
            repo: Repository in format "owner/repo".
            issue_num: Issue number.

        Returns:
            List of comment dicts.
        """
        url = f"{self.BASE_URL}/repos/{repo}/issues/{issue_num}/comments"
        response = self._request("GET", url)
        return response.json()
