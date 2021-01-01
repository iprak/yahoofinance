"""Tests for Yahoo Finance component."""
# import json
import os

# import homeassistant
# import pytest
from custom_components.yahoofinance.const import DOMAIN
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.async_mock import AsyncMock, Mock, patch

VALID_CONFIG = {
    DOMAIN: {
        "symbols": ["xyz"],
        "decimal_places": 0,
    }
}


def load_fixture(filename):
    """Load a fixture."""
    # path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


# @pytest.fixture
async def setup_sensor(hass):
    """Set up sensor."""
    #       return_value=json.loads(load_fixture("yahoofinance.json")),

    print("setup_sensor")
    print(DOMAIN)

    with patch(
        "custom_components.yahoofinance.YahooSymbolUpdateCoordinator"
    ) as mock_coordinator:
        instance = Mock()
        instance.update.return_value = AsyncMock()
        mock_coordinator.return_value = instance

        assert await async_setup_component(hass, DOMAIN, VALID_CONFIG) == True
        await hass.async_block_till_done()

    expected = {"symbols": ["XYZ"]}
    assert expected == hass.data[DOMAIN]["config"]

    expected = {}
    assert expected == hass.data[DOMAIN]["config"]


# async def test_setup(hass, setup_sensor):
#     """Test the setup with custom settings."""
#     state = hass.states.get("sensor.ethereum")
#     assert state is not None

#     assert state.name == "Ethereum"
#     assert state.state == "493.455"
#     assert state.attributes.get("symbol") == "ETH"
#     assert state.attributes.get("unit_of_measurement") == "EUR"
