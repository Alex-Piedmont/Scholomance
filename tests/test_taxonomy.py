"""Tests for the classification taxonomy."""

import pytest

from src.taxonomy import (
    TAXONOMY,
    FieldDefinition,
    get_top_fields,
    get_subfields,
    get_all_subfields,
    get_field_description,
    format_taxonomy_for_prompt,
)


class TestTaxonomyStructure:
    """Tests for taxonomy data structure."""

    def test_taxonomy_exists(self):
        """Test that TAXONOMY is defined and not empty."""
        assert TAXONOMY is not None
        assert len(TAXONOMY) > 0

    def test_taxonomy_has_required_fields(self):
        """Test that taxonomy has the required top-level fields."""
        required_fields = [
            "Robotics",
            "MedTech",
            "Agriculture",
            "Energy",
            "Computing",
            "Materials",
            "Electronics",
            "Biotechnology",
        ]
        for field in required_fields:
            assert field in TAXONOMY, f"Missing required field: {field}"

    def test_field_definition_structure(self):
        """Test that each field has the correct structure."""
        for field_name, definition in TAXONOMY.items():
            assert isinstance(definition, FieldDefinition)
            assert definition.name == field_name
            assert isinstance(definition.description, str)
            assert len(definition.description) > 0
            assert isinstance(definition.subfields, list)
            assert len(definition.subfields) > 0
            assert isinstance(definition.keywords, list)

    def test_other_field_exists(self):
        """Test that 'Other' field exists as fallback."""
        assert "Other" in TAXONOMY


class TestTaxonomyFunctions:
    """Tests for taxonomy helper functions."""

    def test_get_top_fields(self):
        """Test getting list of top fields."""
        fields = get_top_fields()
        assert isinstance(fields, list)
        assert "Robotics" in fields
        assert "MedTech" in fields
        assert len(fields) == len(TAXONOMY)

    def test_get_subfields_valid(self):
        """Test getting subfields for valid field."""
        subfields = get_subfields("Robotics")
        assert isinstance(subfields, list)
        assert len(subfields) > 0
        assert "Industrial Robotics" in subfields or "Autonomous Vehicles" in subfields

    def test_get_subfields_invalid(self):
        """Test getting subfields for invalid field returns empty."""
        subfields = get_subfields("NonexistentField")
        assert subfields == []

    def test_get_all_subfields(self):
        """Test getting all field/subfield pairs."""
        pairs = get_all_subfields()
        assert isinstance(pairs, list)
        assert len(pairs) > 0

        # Each pair should be (top_field, subfield)
        for top_field, subfield in pairs:
            assert top_field in TAXONOMY
            assert subfield in TAXONOMY[top_field].subfields

    def test_get_field_description_valid(self):
        """Test getting description for valid field."""
        description = get_field_description("Robotics")
        assert description is not None
        assert isinstance(description, str)
        assert len(description) > 0

    def test_get_field_description_invalid(self):
        """Test getting description for invalid field returns None."""
        description = get_field_description("NonexistentField")
        assert description is None


class TestPromptFormatting:
    """Tests for prompt formatting."""

    def test_format_taxonomy_for_prompt(self):
        """Test formatting taxonomy for LLM prompt."""
        prompt_text = format_taxonomy_for_prompt()

        assert isinstance(prompt_text, str)
        assert len(prompt_text) > 0

        # Should include field names
        assert "Robotics" in prompt_text
        assert "MedTech" in prompt_text

        # Should include subfields
        assert "Subfields:" in prompt_text

    def test_prompt_includes_all_fields(self):
        """Test that prompt includes all fields."""
        prompt_text = format_taxonomy_for_prompt()

        for field_name in TAXONOMY.keys():
            assert field_name in prompt_text, f"Missing field in prompt: {field_name}"


class TestSubfieldCoverage:
    """Tests for subfield coverage."""

    def test_medtech_subfields(self):
        """Test MedTech has expected subfields."""
        subfields = get_subfields("MedTech")
        expected = ["Diagnostics", "Therapeutics", "Drug Delivery"]

        for expected_sf in expected:
            assert expected_sf in subfields, f"Missing MedTech subfield: {expected_sf}"

    def test_computing_subfields(self):
        """Test Computing has expected subfields."""
        subfields = get_subfields("Computing")
        expected = ["Artificial Intelligence", "Machine Learning", "Cybersecurity"]

        for expected_sf in expected:
            assert expected_sf in subfields, f"Missing Computing subfield: {expected_sf}"

    def test_energy_subfields(self):
        """Test Energy has expected subfields."""
        subfields = get_subfields("Energy")
        expected = ["Solar Energy", "Battery Technology", "Energy Storage"]

        for expected_sf in expected:
            assert expected_sf in subfields, f"Missing Energy subfield: {expected_sf}"
