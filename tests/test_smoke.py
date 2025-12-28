"""Smoke test for sentinel pipeline."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sentinel.agent.loop import run_agent_with_supervisor
from sentinel.config import get_runs_dir
from sentinel.evidence.graph import EvidenceGraph
from sentinel.trace.store_jsonl import JsonlTraceStore


@pytest.fixture
def sample_bundle():
    """Load sample bundle fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_bundle.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_llm_responses():
    """Load mock LLM responses."""
    fixture_path = Path(__file__).parent / "fixtures" / "mock_llm_responses.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.chat = self.Chat(self)

    class Chat:
        def __init__(self, client):
            self.client = client
            self.completions = self.Completions(client)

        class Completions:
            def __init__(self, client):
                self.client = client

            def create(self, **kwargs):
                self.client.call_count += 1
                if self.client.call_count <= len(self.client.responses):
                    response_data = self.client.responses[self.client.call_count - 1]["response"]
                    # Create mock response object
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message = MagicMock()
                    mock_response.choices[0].message.role = response_data["choices"][0]["message"]["role"]
                    mock_response.choices[0].message.content = response_data["choices"][0]["message"].get("content")
                    mock_response.choices[0].message.tool_calls = None

                    if "tool_calls" in response_data["choices"][0]["message"]:
                        tool_calls = response_data["choices"][0]["message"]["tool_calls"]
                        mock_response.choices[0].message.tool_calls = []
                        for tc in tool_calls:
                            mock_tc = MagicMock()
                            mock_tc.id = tc["id"]
                            mock_tc.function = MagicMock()
                            mock_tc.function.name = tc["function"]["name"]
                            mock_tc.function.arguments = tc["function"]["arguments"]
                            mock_response.choices[0].message.tool_calls.append(mock_tc)

                    mock_response.usage = MagicMock()
                    mock_response.usage.prompt_tokens = response_data["usage"]["prompt_tokens"]
                    mock_response.usage.completion_tokens = response_data["usage"]["completion_tokens"]

                    return mock_response
                else:
                    # Return done response
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message = MagicMock()
                    mock_response.choices[0].message.content = "Done"
                    mock_response.choices[0].message.tool_calls = None
                    mock_response.usage = MagicMock()
                    mock_response.usage.prompt_tokens = 100
                    mock_response.usage.completion_tokens = 10
                    return mock_response


def test_smoke_pipeline(sample_bundle, mock_llm_responses, tmp_path):
    """Test full pipeline with mocked components."""
    # Setup
    run_id = "test_run_001"
    runs_dir = get_runs_dir()
    run_dir = runs_dir / run_id
    trace_path = run_dir / "trace" / "events.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    trace_store = JsonlTraceStore(trace_path)
    graph = EvidenceGraph()

    from sentinel.interventions.policy import Supervisor

    supervisor = Supervisor(graph, trace_store)

    # Mock LLM client
    mock_client = MockLLMClient(mock_llm_responses)

    # Mock GitHub fetch to return sample bundle
    with patch("sentinel.agent.loop.fetch_repo_milestone_bundle") as mock_fetch:
        mock_fetch.return_value = sample_bundle

        # Run pipeline
        result = run_agent_with_supervisor(
            "test/repo",
            "v1.0.0",
            run_id,
            trace_store,
            supervisor,
            llm_client=mock_client,
        )

    # Assertions
    assert result["run_id"] == run_id
    assert result["event_count"] >= 10  # Should have multiple events
    assert Path(result["report_path"]).exists()

    # Check trace file
    events = list(trace_store.iter_events())
    assert len(events) >= 10

    # Check that we have different event types
    event_types = {e.type for e in events}
    assert "tool_call" in event_types or "llm_call" in event_types

    trace_store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
