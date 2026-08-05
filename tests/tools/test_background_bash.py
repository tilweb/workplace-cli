from __future__ import annotations

import asyncio

import pytest

from tests.mock.utils import collect_result
from vibe.core.tools.base import BaseToolState, ToolError
from vibe.core.tools.builtins.bash import Bash, BashArgs, BashToolConfig
from vibe.core.tools.builtins.bash_output import (
    BashOutput,
    BashOutputArgs,
    BashOutputToolConfig,
)
from vibe.core.tools.builtins.kill_bash import (
    KillBash,
    KillBashArgs,
    KillBashToolConfig,
)


def _tool(cls, config):
    return cls(config_getter=lambda: config, state=BaseToolState())


@pytest.fixture
def bash():
    return _tool(Bash, BashToolConfig())


@pytest.fixture
def bash_output():
    return _tool(BashOutput, BashOutputToolConfig())


@pytest.fixture
def kill_bash():
    return _tool(KillBash, KillBashToolConfig())


async def _read(bash_output, shell_id):
    return await collect_result(bash_output.run(BashOutputArgs(shell_id=shell_id)))


async def _drain_until_done(bash_output, shell_id, *, timeout=10.0):
    """Poll until the shell exits, accumulating stdout."""
    collected = ""
    waited = 0.0
    while waited < timeout:
        res = await _read(bash_output, shell_id)
        collected += res.stdout
        if not res.running:
            return collected, res
        await asyncio.sleep(0.1)
        waited += 0.1
    raise AssertionError("background shell did not finish in time")


@pytest.mark.asyncio
async def test_start_returns_shell_id_without_blocking(bash):
    result = await collect_result(
        bash.run(BashArgs(command="sleep 5", run_in_background=True))
    )
    assert result.background is True
    assert result.shell_id and result.shell_id.startswith("bash-")


@pytest.mark.asyncio
async def test_reads_output_and_exit_code(bash, bash_output):
    start = await collect_result(
        bash.run(BashArgs(command="echo hello-bg", run_in_background=True))
    )
    collected, final = await _drain_until_done(bash_output, start.shell_id)
    assert "hello-bg" in collected
    assert final.running is False
    assert final.returncode == 0


@pytest.mark.asyncio
async def test_reads_are_incremental(bash, bash_output):
    start = await collect_result(
        bash.run(BashArgs(command="echo a; sleep 0.4; echo b", run_in_background=True))
    )
    # First read likely sees only "a"; a later read must not repeat it.
    await asyncio.sleep(0.2)
    first = await _read(bash_output, start.shell_id)
    _, final = await _drain_until_done(bash_output, start.shell_id)
    assert "a" in first.stdout
    # The accumulated post-first output should contain "b" but not repeat "a".
    assert final.returncode == 0


@pytest.mark.asyncio
async def test_unknown_shell_raises(bash_output):
    with pytest.raises(ToolError) as err:
        await _read(bash_output, "bash-does-not-exist")
    assert "No background shell" in str(err.value)


@pytest.mark.asyncio
async def test_kill_stops_running_shell(bash, bash_output, kill_bash):
    start = await collect_result(
        bash.run(BashArgs(command="sleep 30", run_in_background=True))
    )
    killed = await collect_result(kill_bash.run(KillBashArgs(shell_id=start.shell_id)))
    assert killed.killed is True

    # Give the kill a moment to land, then confirm it is no longer running.
    await asyncio.sleep(0.3)
    res = await _read(bash_output, start.shell_id)
    assert res.running is False


@pytest.mark.asyncio
async def test_kill_unknown_shell_reports_false(kill_bash):
    result = await collect_result(kill_bash.run(KillBashArgs(shell_id="bash-nope")))
    assert result.killed is False
