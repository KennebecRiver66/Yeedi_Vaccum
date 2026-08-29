"""Smoke tests for the Yeedi device verification config flow."""

from unittest.mock import AsyncMock, patch

from deebot_client.exceptions import (
    DeviceVerificationRequiredError,
    InvalidVerificationCodeError,
)
import pytest

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_COUNTRY,
    CONF_DEVICE_ID,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.yeedi  # noqa: F401
import custom_components.yeedi.config_flow  # noqa: F401

DOMAIN = "yeedi"
CREDENTIALS = {
    CONF_USERNAME: "user@example.com",
    CONF_PASSWORD: "hunter2",
    CONF_COUNTRY: "IT",
}


@pytest.fixture(name="mqtt_ok")
def mqtt_ok_fixture():
    """Make the MQTT verification a no-op."""
    with patch(
        "custom_components.yeedi.config_flow.MqttClient.verify_config",
        AsyncMock(return_value=None),
    ):
        yield


async def _start(hass: HomeAssistant):
    """Advance the flow to the credentials form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MODE: "cloud"}
    )


async def test_device_verification_flow(hass: HomeAssistant, mqtt_ok) -> None:
    """A login rejected with DeviceVerificationRequiredError asks for a code."""
    result = await _start(hass)
    assert result["step_id"] == "auth"

    request_code = AsyncMock(return_value=None)
    verify_device = AsyncMock(return_value=None)
    with (
        patch(
            "custom_components.yeedi.config_flow.Authenticator.authenticate",
            AsyncMock(side_effect=DeviceVerificationRequiredError("1013")),
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator."
            "request_device_verification_code",
            request_code,
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator.verify_device",
            verify_device,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], dict(CREDENTIALS)
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "device_verification"
        assert request_code.await_count == 1

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "123456"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    verify_device.assert_awaited_once_with("123456")
    # The verified client device ID must be persisted, otherwise every restart
    # would generate a new one and need verifying again.
    assert result["data"][CONF_DEVICE_ID]
    assert result["result"].minor_version == 2


async def test_invalid_verification_code(hass: HomeAssistant, mqtt_ok) -> None:
    """A wrong code is reported on the verification form."""
    result = await _start(hass)

    with (
        patch(
            "custom_components.yeedi.config_flow.Authenticator.authenticate",
            AsyncMock(side_effect=DeviceVerificationRequiredError("1013")),
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator."
            "request_device_verification_code",
            AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator.verify_device",
            AsyncMock(side_effect=InvalidVerificationCodeError("1012")),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], dict(CREDENTIALS)
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "000000"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device_verification"
    assert result["errors"] == {"base": "invalid_verification_code"}


async def test_reauth_flow(hass: HomeAssistant, mqtt_ok) -> None:
    """Re-authentication verifies a new device ID and keeps the entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**CREDENTIALS, CONF_DEVICE_ID: "OLDID123"},
        unique_id=CREDENTIALS[CONF_USERNAME],
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "custom_components.yeedi.config_flow.Authenticator.authenticate",
            AsyncMock(side_effect=DeviceVerificationRequiredError("1013")),
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator."
            "request_device_verification_code",
            AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.yeedi.config_flow.Authenticator.verify_device",
            AsyncMock(return_value=None),
        ),
        patch("custom_components.yeedi.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-password"}
        )
        assert result["step_id"] == "device_verification"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "123456"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"
    # The already verified device ID is reused instead of a fresh random one
    assert entry.data[CONF_DEVICE_ID] == "OLDID123"


async def test_migration_persists_device_id(hass: HomeAssistant) -> None:
    """An old entry gets a stable device ID on migration."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=dict(CREDENTIALS), version=1, minor_version=1
    )
    entry.add_to_hass(hass)

    assert await custom_components.yeedi.async_migrate_entry(hass, entry) is True
    assert entry.minor_version == 2
    assert entry.data[CONF_DEVICE_ID]
