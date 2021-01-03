"""Tests for Yahoo Finance component."""
import json
import os

import pytest


def load_json(filename):
    """Load sample JSON."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


@pytest.fixture
def mock_json():
    """Return sample JSON data."""
    yield json.loads(load_json("yahoofinance.json"))
