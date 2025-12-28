import os
import time
from typing import Dict, List, Optional

import requests


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def _check_rate_limit(self):
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
        self._check_rate_limit()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 403:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        raise requests.RequestException("Failed after retries")

    def get_milestones(self, repo: str) -> List[Dict]:
        url = f"{self.BASE_URL}/repos/{repo}/milestones"
        response = self._request("GET", url, params={"state": "all"})
        return response.json()

    def get_issues(self, repo: str, milestone: Optional[str] = None) -> List[Dict]:
        url = f"{self.BASE_URL}/repos/{repo}/issues"
        params = {"state": "all"}
        if milestone:
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
        url = f"{self.BASE_URL}/repos/{repo}/issues/{issue_num}"
        response = self._request("GET", url)
        return response.json()

    def get_comments(self, repo: str, issue_num: int) -> List[Dict]:
        url = f"{self.BASE_URL}/repos/{repo}/issues/{issue_num}/comments"
        response = self._request("GET", url)
        return response.json()
