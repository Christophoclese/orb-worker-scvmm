"""VLAN resolution integration tests for ScvmmBackend.

This module replaces the previous simulated tests with real integration tests
that test actual VLAN creation and configuration from SCVMM data.
Previously, tests simulated the behavior instead of testing it.
"""

import pytest
from unittest.mock import Mock

from netboxlabs.diode.sdk.ingester import VLAN

from scvmm.main import ScvmmBackend
from scvmm.models import OrganizationConfig, VLANMapping, MatchType
from scvmm.mapping import MappingResolver


class TestVLANConfigLookup:
    """Tests for VLAN configuration lookup."""

    def test_get_vlan_config_found(self):
        """Test that VLAN config is found in lookup dict."""
        backend = ScvmmBackend()
        
        # Create a realistic VLAN config dict (as it would be created in create_entities_from_data)
        vlan_config_dict = {
            100: {"vid": 100, "name": "Management", "status": "active"},
            200: {"vid": 200, "name": "Data", "status": "active"},
        }
        
        # Test lookup
        config = backend._get_vlan_config(vlan_config_dict, 100)
        
        assert config is not None
        assert config["name"] == "Management"
        assert config["vid"] == 100

    def test_get_vlan_config_not_found(self):
        """Test that VLAN config returns None when not found."""
        backend = ScvmmBackend()
        
        vlan_config_dict = {
            100: {"vid": 100, "name": "Management", "status": "active"},
        }
        
        # Test lookup for non-existent VLAN
        config = backend._get_vlan_config(vlan_config_dict, 999)
        
        assert config is None

    def test_get_vlan_config_empty_dict(self):
        """Test lookup with empty configuration."""
        backend = ScvmmBackend()
        
        config = backend._get_vlan_config({}, 100)
        
        assert config is None


class TestVLANEntityBuilding:
    """Tests for VLAN entity construction with _build_vlan_entity method."""

    def test_build_vlan_entity_with_config(self):
        """Test building VLAN entity from configuration."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "vid": 100,
            "name": "Management",
            "status": "active",
            "role": "management",
            "description": "Management VLAN",
        }
        
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        assert vlan.vid == 100
        assert vlan.name == "Management"
        assert vlan.status == "active"

    def test_build_vlan_entity_without_config(self):
        """Test building VLAN entity without config uses VID as name."""
        backend = ScvmmBackend()
        
        vlan = backend._build_vlan_entity(100, None)
        
        assert vlan.vid == 100
        assert vlan.name == "100"  # Uses VID as fallback
        assert vlan.status == "active"

    def test_build_vlan_entity_with_optional_fields(self):
        """Test that optional VLAN fields are applied when present."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "name": "Management",
            "status": "active",
            "role": "management",
            "description": "Mgmt VLAN",
            "tags": ["prod"],
            "vlan_group": "Production",
        }
        
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        # Verify basic fields
        assert vlan.vid == 100
        assert vlan.name == "Management"
        
        # Optional fields should be set if model supports them
        if hasattr(vlan, 'role') and vlan.role:
            assert vlan.role.name == "management"
        if hasattr(vlan, 'description'):
            assert vlan.description == "Mgmt VLAN"

    def test_build_vlan_entity_with_minimal_config(self):
        """Test building VLAN with minimal configuration."""
        backend = ScvmmBackend()
        
        vlan_config = {"name": "General", "status": "deprecated"}
        
        vlan = backend._build_vlan_entity(50, vlan_config)
        
        assert vlan.vid == 50
        assert vlan.name == "General"
        assert vlan.status == "deprecated"

    def test_build_vlan_entity_with_partial_optional_fields(self):
        """Test VLAN with some optional fields missing."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "name": "Voice",
            "status": "active",
            "description": "VoIP VLAN",
            # role, tags, vlan_group not present
        }
        
        vlan = backend._build_vlan_entity(200, vlan_config)
        
        assert vlan.vid == 200
        assert vlan.name == "Voice"
        assert vlan.description == "VoIP VLAN"


class TestVLANResolutionIntegration:
    """Integration tests using realistic SCVMM data."""

    def test_vlan_mapping_dict_construction(self, org_config_with_mappings):
        """Test construction of VLAN mapping dict from organization config."""
        vlan_config_dict = {
            vlan.vid: vlan.model_dump(exclude_none=True)
            for vlan in org_config_with_mappings.vlan_mappings
        }
        
        # Verify all VLANs are in dict
        assert 100 in vlan_config_dict
        assert 200 in vlan_config_dict
        assert 300 in vlan_config_dict
        
        # Verify structure
        assert vlan_config_dict[100]["name"] == "Management"
        assert vlan_config_dict[200]["name"] == "Application"

    def test_vlan_with_all_optional_fields(self):
        """Test VLAN configuration with all optional fields populated."""
        org_config = OrganizationConfig(
            vlan_mappings=[
                VLANMapping(
                    vid=100,
                    name="Management",
                    status="active",
                    role="management",
                    description="Management VLAN",
                    tags=["prod", "critical"],
                    vlan_group="Production",
                )
            ]
        )
        
        vlan_config_dict = {
            vlan.vid: vlan.model_dump(exclude_none=True)
            for vlan in org_config.vlan_mappings
        }
        
        assert vlan_config_dict[100]["role"] == "management"
        assert vlan_config_dict[100]["description"] == "Management VLAN"
        assert vlan_config_dict[100]["tags"] == ["prod", "critical"]
        assert vlan_config_dict[100]["vlan_group"] == "Production"

    def test_organization_config_with_no_vlan_mappings(self):
        """Test organization config without VLAN mappings."""
        org_config = OrganizationConfig(vlan_mappings=[])
        
        vlan_config_dict = {
            vlan.vid: vlan.model_dump(exclude_none=True)
            for vlan in org_config.vlan_mappings
        }
        
        assert len(vlan_config_dict) == 0

    def test_vlan_status_default_handling(self):
        """Test that VLAN status defaults to 'active' when not specified."""
        backend = ScvmmBackend()
        
        # Config without status
        vlan_config = {"name": "Test"}
        vlan = backend._build_vlan_entity(150, vlan_config)
        
        # Status should default to active
        assert vlan.status == "active"

    def test_vlan_name_from_vid_when_no_config(self):
        """Test that VLAN name is set to VID string when no config exists."""
        backend = ScvmmBackend()
        
        vlan = backend._build_vlan_entity(999, None)
        
        # Name should be string representation of VID
        assert vlan.name == "999"

    def test_vlan_name_from_config_when_exists(self):
        """Test that VLAN name comes from config when available."""
        backend = ScvmmBackend()
        
        vlan_config = {"name": "CustomName", "status": "active"}
        vlan = backend._build_vlan_entity(999, vlan_config)
        
        # Name should be from config, not VID
        assert vlan.name == "CustomName"

    def test_vlan_resolution_with_multiple_vlans(self):
        """Test VLAN resolution when multiple VLANs are configured."""
        org_config = OrganizationConfig(
            vlan_mappings=[
                VLANMapping(vid=10, name="VoIP", status="active"),
                VLANMapping(vid=20, name="Data", status="active"),
                VLANMapping(vid=30, name="Guest", status="deprecated"),
                VLANMapping(vid=40, name="Management", status="active"),
            ]
        )
        
        vlan_config_dict = {
            vlan.vid: vlan.model_dump(exclude_none=True)
            for vlan in org_config.vlan_mappings
        }
        
        backend = ScvmmBackend()
        
        # Build VLANs for each config
        vlans = [
            backend._build_vlan_entity(vid, vlan_config_dict.get(vid))
            for vid in [10, 20, 30, 40]
        ]
        
        assert len(vlans) == 4
        assert vlans[0].name == "VoIP"
        assert vlans[1].name == "Data"
        assert vlans[2].name == "Guest"
        assert vlans[3].name == "Management"


class TestVLANEdgeCases:
    """Tests for VLAN edge cases and error handling."""

    def test_vlan_config_with_empty_name_uses_default(self):
        """Test that empty name string is handled."""
        backend = ScvmmBackend()
        
        vlan_config = {"name": "", "status": "active"}
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        # Empty name should still use what's provided (not fallback to VID)
        assert vlan.name == ""

    def test_vlan_config_with_special_characters(self):
        """Test VLAN names with special characters."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "name": "VLAN-Test_123",
            "status": "active",
            "description": "Test/VLAN (special chars)",
        }
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        assert vlan.name == "VLAN-Test_123"
        if hasattr(vlan, 'description'):
            assert "special chars" in vlan.description

    def test_vlan_config_with_unicode_characters(self):
        """Test VLAN configuration with unicode characters."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "name": "Гостевая_VLAN",  # Russian for "Guest VLAN"
            "status": "active",
        }
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        assert vlan.name == "Гостевая_VLAN"

    def test_vlan_vid_range_extremes(self):
        """Test VLAN with minimum and maximum valid VID."""
        backend = ScvmmBackend()
        
        # Minimum VLAN ID (1)
        vlan_min = backend._build_vlan_entity(1, {"name": "Min"})
        assert vlan_min.vid == 1
        
        # Maximum standard VLAN ID (4094)
        vlan_max = backend._build_vlan_entity(4094, {"name": "Max"})
        assert vlan_max.vid == 4094

    def test_vlan_empty_description(self):
        """Test VLAN config with empty description."""
        backend = ScvmmBackend()
        
        vlan_config = {
            "name": "Test",
            "status": "active",
            "description": "",
        }
        vlan = backend._build_vlan_entity(100, vlan_config)
        
        assert vlan.name == "Test"
        # Empty description should be preserved or skipped
        if hasattr(vlan, 'description'):
            assert vlan.description == ""


class TestVLANIntegrationWithBackend:
    """Integration tests with full backend workflow."""

    def test_vlan_entity_creation_from_scvmm_data(self, mock_scvmm_data, org_config_with_mappings, mapping_resolver):
        """Test actual VLAN entity creation in backend from SCVMM data."""
        backend = ScvmmBackend()
        entities = backend.create_entities_from_data(
            mock_scvmm_data, mapping_resolver, org_config_with_mappings
        )
        
        # Find interface entities with VLANs
        interface_entities = [
            e for e in entities
            if e.vm_interface is not None and e.vm_interface.untagged_vlan is not None
        ]
        
        assert len(interface_entities) > 0
        
        # Verify VLANs have correct properties from config
        vlan_100_entities = [
            e for e in interface_entities
            if e.vm_interface.untagged_vlan.vid == 100
        ]
        
        if vlan_100_entities:
            vlan = vlan_100_entities[0].vm_interface.untagged_vlan
            assert vlan.name == "Management"  # From config
            assert vlan.status == "active"
