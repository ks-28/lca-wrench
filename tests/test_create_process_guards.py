"""Guards for model process create — no Brightway data required."""

import pytest

from lca_wrench import models


def test_create_process_rejects_blank_unit_before_db():
    with pytest.raises(ValueError, match="Einheit"):
        models.create_process("no-such-db", "Rahmen", unit="", location="CH")


def test_create_process_rejects_blank_location_before_db():
    with pytest.raises(ValueError, match="Ort"):
        models.create_process("no-such-db", "Rahmen", unit="kilogram", location="  ")
