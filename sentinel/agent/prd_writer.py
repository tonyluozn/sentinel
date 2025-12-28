import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from sentinel.trace.schema import EventType, new_event
from sentinel.trace.store_jsonl import JsonlTraceStore


class PRDAgent:
    def __init__(
        self,
        bundle: Dict,
        output_dir: Path,
        trace_store: JsonlTraceStore,
        llm_client: Optional[Any] = None,
        max_iterations: int = 100,
    ):
        self.bundle = bundle
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_store = trace_store
        self.max_iterations = max_iterations

        if llm_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.llm_client = OpenAI(api_key=api_key)
        else:
            self.llm_client = llm_client

        self.tools = {
            "github_fetch_issue": self._tool_github_fetch_issue,
            "github_fetch_comments": self._tool_github_fetch_comments,
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "search_issues": self._tool_search_issues,
            "list_issues": self._tool_list_issues,
        }

        self.context = {
            "bundle": bundle,
            "artifacts": {},
            "observations": [],
        }

    def _tool_github_fetch_issue(self, issue_num: int) -> Dict:
        for issue in self.bundle.get("issues", []):
            if issue.get("number") == issue_num:
                return issue
        return {"error": f"Issue {issue_num} not found"}

    def _tool_github_fetch_comments(self, issue_num: int) -> List[Dict]:
        return []

    def _tool_read_file(self, path: str) -> str:
        file_path = Path(path)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _tool_write_file(self, path: str, content: str) -> Dict:
        file_path = self.output_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        if path.endswith((".md", ".txt")):
            self.trace_store.append(
                new_event(
                    EventType.ARTIFACT,
                    {
                        "path": str(file_path),
                        "type": "document",
                        "name": file_path.name,
                    },
                )
            )

        return {"status": "success", "path": str(file_path)}

    def _tool_search_issues(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        matches = []
        for issue in self.bundle.get("issues", []):
            title = issue.get("title", "").lower()
            body = issue.get("body", "").lower()
            if query_lower in title or query_lower in body:
                matches.append(issue)
        return matches

    def _tool_list_issues(self) -> List[Dict]:
        """List all available issues with their numbers and titles."""
        return [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
            }
            for issue in self.bundle.get("issues", [])
        ]

    def run(self) -> Dict[str, Path]:
        iteration = 0

        system_prompt = """You are an agent that generates Product Requirements Documents (PRD) and Launch Plans from GitHub milestone data.

Your goal is to:
1. Analyze the GitHub milestone and issues
2. Generate a comprehensive PRD.md with sections: Goals, Non-goals, Scope, Metrics, Risks
3. Generate a LAUNCH_PLAN.md with rollout strategy

You have access to tools to fetch issue details, read/write files, and search issues.
Use the tools to gather information and write the documents incrementally."""

        tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "github_fetch_issue",
                    "description": "Fetch details of a specific issue by number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "issue_num": {"type": "integer", "description": "Issue number"},
                        },
                        "required": ["issue_num"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "File content"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_issues",
                    "description": "Search issues by keyword",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_issues",
                    "description": "List all available issues with their numbers and titles. Use this to see which issue numbers are available before fetching specific issues.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        ]

        # Build list of available issue numbers and titles for the prompt
        issues = self.bundle.get("issues", [])
        issue_summary = "\n".join(
            [
                f"  - #{issue.get('number')}: {issue.get('title', 'Untitled')}"
                for issue in issues[:20]  # Show first 20 to avoid overwhelming the prompt
            ]
        )
        if len(issues) > 20:
            issue_summary += f"\n  ... and {len(issues) - 20} more issues"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Generate PRD and Launch Plan for milestone: {self.bundle['milestone']['title']}

Repository: {self.bundle['repo']['full_name']}
Total issues: {len(issues)} issues in this milestone

Available issues:
{issue_summary}

You can use the list_issues tool to see all issues, or search_issues to find issues by keyword.
Start by exploring the issues and then write PRD.md and LAUNCH_PLAN.md.""",
            },
        ]

        while iteration < self.max_iterations:
            iteration += 1

            try:
                call_kwargs = {
                    "model": "gpt-4",
                    "messages": messages,
                    "tools": tool_definitions,
                    "tool_choice": "auto",
                }

                response = self.llm_client.chat.completions.create(**call_kwargs)

                self.trace_store.append(
                    new_event(
                        EventType.LLM_CALL,
                        {
                            "model": "gpt-4",
                            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                            "iteration": iteration,
                        },
                    )
                )

                message = response.choices[0].message
                messages.append(message)

                if message.content and "done" in message.content.lower():
                    break

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name

                        try:
                            params = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            params = {}

                        self.trace_store.append(
                            new_event(
                                EventType.TOOL_CALL,
                                {
                                    "tool": tool_name,
                                    "parameters": params,
                                    "tool_call_id": tool_call.id,
                                },
                            )
                        )

                        if tool_name in self.tools:
                            try:
                                result = self.tools[tool_name](**params)
                            except Exception as e:
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                        self.trace_store.append(
                            new_event(
                                EventType.OBSERVATION,
                                {
                                    "tool_call_id": tool_call.id,
                                    "result": result,
                                },
                            )
                        )

                        self.context["observations"].append(result)

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result) if not isinstance(result, str) else result,
                            }
                        )
                else:
                    if message.content and ("complete" in message.content.lower() or "finished" in message.content.lower()):
                        break

            except Exception as e:
                self.trace_store.append(
                    new_event(
                        EventType.OBSERVATION,
                        {
                            "error": str(e),
                            "iteration": iteration,
                        },
                    )
                )
                break

        artifacts = {}
        for file_path in self.output_dir.glob("*.md"):
            artifacts[file_path.stem] = file_path

        return artifacts
