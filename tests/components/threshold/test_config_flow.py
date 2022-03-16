"""Test the Threshold config flow."""
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.components.threshold.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from tests.common import MockConfigEntry


async def test_config_flow(hass: HomeAssistant) -> None:
    """Test the config flow."""
    input_sensor = "sensor.input"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.threshold.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"entity_id": input_sensor, "lower": -2, "upper": None, "mode": "lower"},
        )
        await hass.async_block_till_done()

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "input threshold"
    assert result["data"] == {}
    assert result["options"] == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": -2.0,
        "mode": "lower",
        "upper": None,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "lower": -2.0,
        "mode": "lower",
        "upper": None,
    }
    assert config_entry.title == "input threshold"


@pytest.mark.parametrize(
    "mode,extra_input_data,extra_expected_data",
    (
        ("lower", {"lower": -2.0}, {"lower": -2.0, "upper": None}),
        ("range", {"lower": -2.0, "upper": 2.0}, {"lower": -2.0, "upper": 2.0}),
        ("upper", {"upper": 2.0}, {"lower": None, "upper": 2.0}),
    ),
)
async def test_modes(
    hass: HomeAssistant, mode, extra_input_data, extra_expected_data
) -> None:
    """Test selecting threshold modes."""
    input_sensor = "sensor.input"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.threshold.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"entity_id": input_sensor, "mode": mode, **extra_input_data},
        )
        await hass.async_block_till_done()

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "input threshold"
    assert result["data"] == {}
    assert result["options"] == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "mode": mode,
        **extra_expected_data,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "mode": mode,
        **extra_expected_data,
    }


@pytest.mark.parametrize(
    "mode,extra_input_data,error",
    (
        ("lower", {"upper": -2.0}, "lower_needs_lower"),
        ("range", {"lower": -2.0}, "range_needs_lower_upper"),
        ("upper", {"lower": 2.0}, "upper_needs_upper"),
    ),
)
async def test_modes_fail(hass: HomeAssistant, mode, extra_input_data, error) -> None:
    """Test selecting threshold modes."""
    input_sensor = "sensor.input"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entity_id": input_sensor, "mode": mode, **extra_input_data},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {"base": error}


def get_suggested(schema, key):
    """Get suggested value for key in voluptuous schema."""
    for k in schema.keys():
        if k == key:
            if k.description is None or "suggested_value" not in k.description:
                return None
            return k.description["suggested_value"]
    # Wanted key absent from schema
    raise Exception


async def test_options(hass: HomeAssistant) -> None:
    """Test reconfiguring."""
    input_sensor = "sensor.input"
    hass.states.async_set(input_sensor, "10")

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": input_sensor,
            "hysteresis": 0.0,
            "lower": -2.0,
            "mode": "lower",
            "upper": None,
        },
        title="My threshold",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_suggested(schema, "hysteresis") == 0.0
    assert get_suggested(schema, "lower") == -2.0
    assert get_suggested(schema, "mode") == "lower"
    assert get_suggested(schema, "upper") is None

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "hysteresis": 0.0,
            "mode": "upper",
            "upper": 20.0,
        },
    )
    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "mode": "upper",
        "lower": None,
        "upper": 20.0,
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor,
        "hysteresis": 0.0,
        "mode": "upper",
        "lower": None,
        "upper": 20.0,
    }
    assert config_entry.title == "My threshold"

    # Check config entry is reloaded with new options
    await hass.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(hass.states.async_all()) == 2

    # Check the state of the entity has changed as expected
    state = hass.states.get("binary_sensor.my_threshold")
    assert state.state == "off"
    assert state.attributes["type"] == "upper"
