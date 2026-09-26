"""run_agent.py turns a failed triage into a clear exit and an ERROR trace."""

import sys

import mlflow
import pytest

import agent
import run_agent


@pytest.mark.parametrize(
    "error,expected",
    [
        (agent.TriageError("bad fields: route"), "Triage failed: bad fields: route"),
        (RuntimeError("503 UNAVAILABLE"), "Triage failed: RuntimeError: 503 UNAVAILABLE"),
    ],
)
def test_failed_triage_exits_clearly_with_error_trace(monkeypatch, tmp_path, capsys, error, expected):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_agent.py", "T-1"])

    async def failing_triage(ticket_id):
        raise error

    monkeypatch.setattr(agent, "triage", failing_triage)

    with pytest.raises(SystemExit) as exit_info:
        run_agent.main()

    assert str(exit_info.value) == expected
    assert capsys.readouterr().out == ""

    mlflow.flush_trace_async_logging()
    # The trace this run just recorded (the sqlite store is cached per process,
    # so a store-wide search would also see earlier parametrized cases).
    trace = mlflow.get_trace(mlflow.get_last_active_trace_id())
    assert trace.info.state.value == "ERROR"
