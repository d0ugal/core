"""Tests for Transmission init."""

from unittest.mock import patch

import pytest
from transmissionrpc.error import TransmissionError

from homeassistant.components import transmission
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry, mock_coro

MOCK_ENTRY = MockConfigEntry(
    domain=transmission.DOMAIN,
    data={
        transmission.CONF_NAME: "Transmission",
        transmission.CONF_HOST: "0.0.0.0",
        transmission.CONF_USERNAME: "user",
        transmission.CONF_PASSWORD: "pass",
        transmission.CONF_PORT: 9091,
    },
)


@pytest.fixture(name="api")
def mock_transmission_api():
    """Mock an api."""
    with patch("transmissionrpc.Client") as p:
        yield p


@pytest.fixture(name="auth_error")
def mock_api_authentication_error():
    """Mock an api."""
    with patch(
        "transmissionrpc.Client", side_effect=TransmissionError("401: Unauthorized")
    ):
        yield


@pytest.fixture(name="unknown_error")
def mock_api_unknown_error():
    """Mock an api."""
    with patch("transmissionrpc.Client", side_effect=TransmissionError):
        yield


async def test_setup_with_no_config(hass):
    """Test that we do not discover anything or try to set up a Transmission client."""
    assert await async_setup_component(hass, transmission.DOMAIN, {}) is True
    assert transmission.DOMAIN not in hass.data


async def test_setup_with_config(hass, api):
    """Test that we import the config and setup the client."""
    config = {
        transmission.DOMAIN: {
            transmission.CONF_NAME: "Transmission",
            transmission.CONF_HOST: "0.0.0.0",
            transmission.CONF_USERNAME: "user",
            transmission.CONF_PASSWORD: "pass",
            transmission.CONF_PORT: 9091,
        },
        transmission.DOMAIN: {
            transmission.CONF_NAME: "Transmission2",
            transmission.CONF_HOST: "0.0.0.1",
            transmission.CONF_USERNAME: "user",
            transmission.CONF_PASSWORD: "pass",
            transmission.CONF_PORT: 9091,
        },
    }
    assert await async_setup_component(hass, transmission.DOMAIN, config) is True


async def test_successful_config_entry(hass, api):
    """Test that configured transmission is configured successfully."""

    entry = MOCK_ENTRY
    entry.add_to_hass(hass)

    assert await transmission.async_setup_entry(hass, entry) is True
    assert entry.options == {
        transmission.CONF_SCAN_INTERVAL: transmission.DEFAULT_SCAN_INTERVAL,
        transmission.CONF_LIMIT: transmission.DEFAULT_LIMIT,
        transmission.CONF_ORDER: transmission.DEFAULT_ORDER,
    }


async def test_setup_failed(hass):
    """Test transmission failed due to an error."""

    entry = MOCK_ENTRY
    entry.add_to_hass(hass)

    # test connection error raising ConfigEntryNotReady
    with patch(
        "transmissionrpc.Client",
        side_effect=TransmissionError("111: Connection refused"),
    ), pytest.raises(ConfigEntryNotReady):

        await transmission.async_setup_entry(hass, entry)

    # test Authentication error returning false

    with patch(
        "transmissionrpc.Client", side_effect=TransmissionError("401: Unauthorized")
    ):

        assert await transmission.async_setup_entry(hass, entry) is False


async def test_unload_entry(hass, api):
    """Test removing transmission client."""
    entry = MOCK_ENTRY
    entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries, "async_forward_entry_unload", return_value=mock_coro(True)
    ) as unload_entry:
        assert await transmission.async_setup_entry(hass, entry)

        assert await transmission.async_unload_entry(hass, entry)
        assert unload_entry.call_count == 2
        assert entry.entry_id not in hass.data[transmission.DOMAIN]


async def test_add_torrent_minimal(hass, api):
    """Test that the service call passes no additional arguments when they are not provided."""
    config = {
        transmission.DOMAIN: {
            transmission.CONF_NAME: "Transmission",
            transmission.CONF_HOST: "0.0.0.0",
            transmission.CONF_USERNAME: "user",
            transmission.CONF_PASSWORD: "pass",
            transmission.CONF_PORT: 9091,
        },
    }
    assert await async_setup_component(hass, transmission.DOMAIN, config) is True

    torrent_link = "magnet:..."

    await hass.services.async_call(
        transmission.DOMAIN,
        transmission.SERVICE_ADD_TORRENT,
        {
            transmission.CONF_NAME: transmission.DEFAULT_NAME,
            transmission.ATTR_TORRENT: torrent_link,
        },
        blocking=True,
    )

    await hass.async_block_till_done()

    api().add_torrent.assert_called_with(torrent_link)


async def test_add_torrent_with_args(hass, api):
    """Test that the service call passes the arguments to the client as expected."""
    config = {
        transmission.DOMAIN: {
            transmission.CONF_NAME: "Transmission",
            transmission.CONF_HOST: "0.0.0.0",
            transmission.CONF_USERNAME: "user",
            transmission.CONF_PASSWORD: "pass",
            transmission.CONF_PORT: 9091,
        },
    }
    assert await async_setup_component(hass, transmission.DOMAIN, config) is True

    torrent_link = "magnet:..."
    download_dir = "/some/path"
    paused = True

    await hass.services.async_call(
        transmission.DOMAIN,
        transmission.SERVICE_ADD_TORRENT,
        {
            transmission.CONF_NAME: transmission.DEFAULT_NAME,
            transmission.ATTR_TORRENT: torrent_link,
            transmission.ATTR_DOWNLOAD_DIR: download_dir,
            transmission.ATTR_PAUSED: paused,
        },
        blocking=True,
    )

    await hass.async_block_till_done()

    api().add_torrent.assert_called_with(
        torrent_link, download_dir=download_dir, paused=paused
    )
