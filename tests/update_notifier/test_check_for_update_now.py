from __future__ import annotations

import pytest

from tests.update_notifier.adapters.fake_update_gateway import FakeUpdateGateway
from vibe.cli.update_notifier import (
    Update,
    UpdateError,
    UpdateGatewayCause,
    UpdateGatewayError,
    check_for_update_now,
    update_checks_disabled,
)


@pytest.mark.asyncio
async def test_reports_update_available_when_latest_is_greater() -> None:
    gateway = FakeUpdateGateway(update=Update(latest_version="1.2.0"))

    result = await check_for_update_now(gateway, current_version="1.0.0")

    assert result.is_update_available is True
    assert result.latest_version == "1.2.0"
    assert result.current_version == "1.0.0"


@pytest.mark.asyncio
async def test_reports_no_update_when_current_is_latest() -> None:
    gateway = FakeUpdateGateway(update=Update(latest_version="1.0.0"))

    result = await check_for_update_now(gateway, current_version="1.0.0")

    assert result.is_update_available is False
    assert result.latest_version == "1.0.0"


@pytest.mark.asyncio
async def test_reports_no_update_when_current_is_newer_than_latest() -> None:
    gateway = FakeUpdateGateway(update=Update(latest_version="0.9.0"))

    result = await check_for_update_now(gateway, current_version="1.0.0")

    assert result.is_update_available is False


@pytest.mark.asyncio
async def test_reports_no_update_when_no_release_exists() -> None:
    gateway = FakeUpdateGateway(update=None)

    result = await check_for_update_now(gateway, current_version="1.0.0")

    assert result.is_update_available is False
    assert result.latest_version is None


@pytest.mark.asyncio
async def test_raises_update_error_when_gateway_fails() -> None:
    gateway = FakeUpdateGateway(
        error=UpdateGatewayError(cause=UpdateGatewayCause.REQUEST_FAILED)
    )

    with pytest.raises(UpdateError):
        await check_for_update_now(gateway, current_version="1.0.0")


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " On "])
def test_update_checks_disabled_when_env_is_truthy(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("WORKPLACE_NO_UPDATE_CHECK", value)

    assert update_checks_disabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no"])
def test_update_checks_enabled_when_env_is_falsy_or_unset(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("WORKPLACE_NO_UPDATE_CHECK", value)

    assert update_checks_disabled() is False
