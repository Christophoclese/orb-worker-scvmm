#!/usr/bin/env python
"""Tests for scvmm configuration models."""

import pytest
from pydantic import ValidationError

from scvmm.models import (
    MatchType,
    SiteMapping,
    EnvironmentMapping,
    VLANMapping,
    WinRMConfig,
    OrganizationConfig,
)


class TestMatchType:
    """Tests for MatchType enum."""

    def test_match_type_exact(self):
        assert MatchType.EXACT == "exact"

    def test_match_type_prefix(self):
        assert MatchType.PREFIX == "prefix"

    def test_match_type_regex(self):
        assert MatchType.REGEX == "regex"


class TestSiteMapping:
    """Tests for SiteMapping model."""

    def test_valid_site_mapping(self):
        mapping = SiteMapping(code="boi", name="Boise")
        assert mapping.code == "boi"
        assert mapping.name == "Boise"
        assert mapping.match_type == MatchType.PREFIX

    def test_site_mapping_with_all_fields(self):
        mapping = SiteMapping(
            code="ptl",
            name="Portland",
            match_type=MatchType.EXACT,
            description="Portland data center",
        )
        assert mapping.code == "ptl"
        assert mapping.name == "Portland"
        assert mapping.match_type == MatchType.EXACT
        assert mapping.description == "Portland data center"

    def test_site_mapping_empty_code(self):
        with pytest.raises(ValidationError):
            SiteMapping(code="", name="Boise")

    def test_site_mapping_empty_name(self):
        with pytest.raises(ValidationError):
            SiteMapping(code="boi", name="")

    def test_site_mapping_whitespace_code(self):
        with pytest.raises(ValidationError):
            SiteMapping(code="   ", name="Boise")


class TestEnvironmentMapping:
    """Tests for EnvironmentMapping model."""

    def test_valid_environment_mapping(self):
        mapping = EnvironmentMapping(code="prd", name="Production Clusters")
        assert mapping.code == "prd"
        assert mapping.name == "Production Clusters"
        assert mapping.match_type == MatchType.PREFIX

    def test_environment_mapping_with_all_fields(self):
        mapping = EnvironmentMapping(
            code="dev",
            name="Development Clusters",
            match_type=MatchType.REGEX,
            description="Development environment",
        )
        assert mapping.code == "dev"
        assert mapping.name == "Development Clusters"
        assert mapping.match_type == MatchType.REGEX
        assert mapping.description == "Development environment"

    def test_environment_mapping_empty_code(self):
        with pytest.raises(ValidationError):
            EnvironmentMapping(code="", name="Production")

    def test_environment_mapping_empty_name(self):
        with pytest.raises(ValidationError):
            EnvironmentMapping(code="prd", name="")


class TestVLANMapping:
    """Tests for VLANMapping model."""

    def test_valid_vlan_mapping_required_fields_only(self):
        mapping = VLANMapping(vid=100, name="Management")
        assert mapping.vid == 100
        assert mapping.name == "Management"
        assert mapping.status is None
        assert mapping.role is None
        assert mapping.description is None
        assert mapping.tags is None
        assert mapping.vlan_group is None

    def test_vlan_mapping_with_status(self):
        mapping = VLANMapping(vid=100, name="Management", status="active")
        assert mapping.vid == 100
        assert mapping.name == "Management"
        assert mapping.status == "active"

    def test_vlan_mapping_with_all_fields(self):
        mapping = VLANMapping(
            vid=200,
            name="Production",
            status="active",
            role="production",
            description="Production network",
            tags=["prod", "monitored"],
            vlan_group="CoreVLANs",
        )
        assert mapping.vid == 200
        assert mapping.name == "Production"
        assert mapping.status == "active"
        assert mapping.role == "production"
        assert mapping.description == "Production network"
        assert mapping.tags == ["prod", "monitored"]
        assert mapping.vlan_group == "CoreVLANs"

    def test_vlan_mapping_missing_name(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=100)

    def test_vlan_mapping_empty_name(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=100, name="")

    def test_vlan_mapping_whitespace_name(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=100, name="   ")

    def test_vlan_mapping_invalid_status(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=100, name="Test", status="inactive")

    def test_vlan_mapping_status_case_insensitive(self):
        mapping = VLANMapping(vid=100, name="Test", status="ACTIVE")
        assert mapping.status == "active"

    def test_vlan_mapping_valid_statuses(self):
        for status in ["active", "planned", "deprecated"]:
            mapping = VLANMapping(vid=100, name="Test", status=status)
            assert mapping.status == status

    def test_vlan_mapping_zero_vid(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=0, name="Test")

    def test_vlan_mapping_negative_vid(self):
        with pytest.raises(ValidationError):
            VLANMapping(vid=-1, name="Test")

    def test_vlan_mapping_large_vid(self):
        mapping = VLANMapping(vid=4095, name="Extended")
        assert mapping.vid == 4095

    def test_vlan_mapping_with_empty_tags_list(self):
        mapping = VLANMapping(vid=100, name="Test", tags=[])
        assert mapping.tags == []

    def test_vlan_mapping_with_multiple_tags(self):
        tags = ["tag1", "tag2", "tag3"]
        mapping = VLANMapping(vid=100, name="Test", tags=tags)
        assert mapping.tags == tags


class TestWinRMConfig:
    """Tests for WinRMConfig model."""

    def test_default_winrm_config(self):
        config = WinRMConfig()
        assert config.port == 5985
        assert config.protocol == "http"
        assert config.path == "/wsman"
        assert config.transport == "ntlm"
        assert config.server_certificate_validation == "ignore"

    def test_custom_winrm_config(self):
        config = WinRMConfig(
            port=5986,
            protocol="https",
            path="/wsman",
            transport="kerberos",
            server_certificate_validation="validate",
        )
        assert config.port == 5986
        assert config.protocol == "https"
        assert config.transport == "kerberos"
        assert config.server_certificate_validation == "validate"

    def test_invalid_port_too_low(self):
        with pytest.raises(ValidationError):
            WinRMConfig(port=0)

    def test_invalid_port_too_high(self):
        with pytest.raises(ValidationError):
            WinRMConfig(port=65536)

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            WinRMConfig(protocol="ftp")

    def test_protocol_case_insensitive(self):
        config = WinRMConfig(protocol="HTTPS")
        assert config.protocol == "https"

    def test_invalid_transport(self):
        with pytest.raises(ValidationError):
            WinRMConfig(transport="oauth2")

    def test_transport_case_insensitive(self):
        config = WinRMConfig(transport="KERBEROS")
        assert config.transport == "kerberos"

    def test_invalid_certificate_validation(self):
        with pytest.raises(ValidationError):
            WinRMConfig(server_certificate_validation="permissive")

    def test_cert_validation_case_insensitive(self):
        config = WinRMConfig(server_certificate_validation="VALIDATE")
        assert config.server_certificate_validation == "validate"


class TestOrganizationConfig:
    """Tests for OrganizationConfig model."""

    def test_default_organization_config(self):
        config = OrganizationConfig()
        assert config.site_mappings == []
        assert config.environment_mappings == []
        assert config.vlan_mappings == []
        assert config.default_site == "Unknown"
        assert config.default_group == ""

    def test_organization_config_with_site_mappings(self):
        site_mappings = [
            SiteMapping(code="boi", name="Boise"),
            SiteMapping(code="ptl", name="Portland"),
        ]
        config = OrganizationConfig(site_mappings=site_mappings)
        assert len(config.site_mappings) == 2
        assert config.site_mappings[0].name == "Boise"
        assert config.site_mappings[1].name == "Portland"

    def test_organization_config_with_environment_mappings(self):
        env_mappings = [
            EnvironmentMapping(code="prd", name="Production"),
            EnvironmentMapping(code="dev", name="Development"),
        ]
        config = OrganizationConfig(environment_mappings=env_mappings)
        assert len(config.environment_mappings) == 2

    def test_organization_config_custom_defaults(self):
        config = OrganizationConfig(
            default_site="Unclassified",
            default_group="Uncategorized",
        )
        assert config.default_site == "Unclassified"
        assert config.default_group == "Uncategorized"

    def test_organization_config_full(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise"),
                SiteMapping(code="ptl", name="Portland"),
            ],
            environment_mappings=[
                EnvironmentMapping(code="prd", name="Production"),
                EnvironmentMapping(code="dev", name="Development"),
            ],
            default_site="Unknown Site",
            default_group="Unknown Group",
        )
        assert len(config.site_mappings) == 2
        assert len(config.environment_mappings) == 2
        assert config.default_site == "Unknown Site"
        assert config.default_group == "Unknown Group"

    def test_organization_config_with_vlan_mappings(self):
        vlan_mappings = [
            VLANMapping(vid=100, name="Management"),
            VLANMapping(vid=200, name="Production", status="active"),
        ]
        config = OrganizationConfig(vlan_mappings=vlan_mappings)
        assert len(config.vlan_mappings) == 2
        assert config.vlan_mappings[0].vid == 100
        assert config.vlan_mappings[1].name == "Production"

    def test_organization_config_full_with_vlans(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise"),
            ],
            environment_mappings=[
                EnvironmentMapping(code="prd", name="Production"),
            ],
            vlan_mappings=[
                VLANMapping(vid=100, name="Management"),
                VLANMapping(vid=200, name="Production", role="production"),
            ],
            default_site="Unknown Site",
            default_group="Unknown Group",
        )
        assert len(config.site_mappings) == 1
        assert len(config.environment_mappings) == 1
        assert len(config.vlan_mappings) == 2
        assert config.default_site == "Unknown Site"
