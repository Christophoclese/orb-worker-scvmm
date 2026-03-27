"""Test configuration and fixtures for SCVMM backend tests."""

import pytest
import json
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

from scvmm.models import (
    OrganizationConfig,
    SiteMapping,
    EnvironmentMapping,
    VLANMapping,
    MatchType,
    WinRMConfig,
)
from scvmm.mapping import MappingResolver


# ============================================================================
# Mock SCVMM Data Fixtures
# ============================================================================

@pytest.fixture
def mock_scvmm_data() -> Dict[str, Any]:
    """Realistic mock SCVMM data with clusters, VMs, interfaces, disks, and VLANs."""
    return {
        "Clusters": [
            {
                "Name": "cluster1",
                "ClusterName": "CLUSTER-01",
                "DomainName": "example.com",
                "Description": "Production cluster",
                "Hosts": [
                    "host1.example.com",
                    "host2.example.com",
                ],
            },
            {
                "Name": "cluster2",
                "ClusterName": "CLUSTER-02",
                "DomainName": "example.com",
                "Description": "Development cluster",
                "Hosts": [
                    "host3.example.com",
                ],
            },
        ],
        "VMs": [
            {
                "Name": "prod-vm-01",
                "Description": "Production application server",
                "CPUCount": 4,
                "Memory": 8192,
                "OperatingSystem": "Windows Server 2019",
                "Status": "Running",
                "HostName": "host1.example.com",
                "ClusterName": "CLUSTER-01",
                "Interfaces": [
                    {
                        "Name": "Network Adapter 1",
                        "MacAddress": "00:11:22:33:44:55",
                        "Enabled": True,
                        "Mode": "access",
                        "UntaggedVlan": 100,
                        "IPv4Addresses": ["192.168.100.10"],
                        "IPv4Subnets": ["192.168.100.0/24"],
                    },
                    {
                        "Name": "Network Adapter 2",
                        "MacAddress": "00:11:22:33:44:56",
                        "Enabled": True,
                        "Mode": "access",
                        "UntaggedVlan": 200,
                        "IPv4Addresses": ["192.168.200.10"],
                        "IPv4Subnets": ["192.168.200.0/24"],
                    },
                ],
                "Disks": [
                    {
                        "Name": "OS_Disk",
                        "VHDFormatType": "vhdx",
                        "Size": 100,
                    },
                    {
                        "Name": "Data_Disk",
                        "VHDFormatType": "vhdx",
                        "Size": 500,
                    },
                ],
            },
            {
                "Name": "dev-vm-01",
                "Description": "Development test server",
                "CPUCount": 2,
                "Memory": 4096,
                "OperatingSystem": "Windows Server 2016",
                "Status": "PowerOff",
                "HostName": "host3.example.com",
                "ClusterName": "CLUSTER-02",
                "Interfaces": [
                    {
                        "Name": "Network Adapter 1",
                        "MacAddress": "00:11:22:33:44:77",
                        "Enabled": True,
                        "Mode": None,
                        "UntaggedVlan": None,
                        "IPv4Addresses": [],
                        "IPv4Subnets": [],
                    },
                ],
                "Disks": [
                    {
                        "Name": "SystemDrive",
                        "VHDFormatType": "vhdx",
                        "Size": 60,
                    },
                ],
            },
            {
                "Name": "standalone-vm",
                "Description": "Standalone VM not in a cluster",
                "CPUCount": 1,
                "Memory": 2048,
                "OperatingSystem": "Windows 10",
                "Status": "Paused",
                "HostName": "standalone-host.example.com",
                "ClusterName": None,
                "Interfaces": [
                    {
                        "Name": "Network Adapter 1",
                        "MacAddress": "00:11:22:33:44:88",
                        "Enabled": False,
                        "Mode": "access",
                        "UntaggedVlan": 300,
                        "IPv4Addresses": [],
                        "IPv4Subnets": [],
                    },
                ],
                "Disks": [
                    {
                        "Name": "MainDisk",
                        "VHDFormatType": "vhdx",
                        "Size": 50,
                    },
                ],
            },
        ],
    }


@pytest.fixture
def minimal_scvmm_data() -> Dict[str, Any]:
    """Minimal SCVMM data for edge case testing."""
    return {
        "Clusters": [],
        "VMs": [
            {
                "Name": "empty-vm",
                "Description": "",
                "CPUCount": 1,
                "Memory": 512,
                "OperatingSystem": "",
                "Status": "Running",
                "HostName": "test-host",
                "ClusterName": None,
                "Interfaces": [],
                "Disks": [],
            },
        ],
    }


# ============================================================================
# Organization Configuration Fixtures
# ============================================================================

@pytest.fixture
def org_config_with_mappings() -> OrganizationConfig:
    """Organization config with site, environment, and VLAN mappings."""
    return OrganizationConfig(
        site_mappings=[
            SiteMapping(
                match_type=MatchType.EXACT,
                code="cluster1",
                name="Site-Prod",
            ),
            SiteMapping(
                match_type=MatchType.PREFIX,
                code="cluster",
                name="Site-Default",
            ),
        ],
        environment_mappings=[
            EnvironmentMapping(
                match_type=MatchType.EXACT,
                code="cluster1",
                name="production",
            ),
            EnvironmentMapping(
                match_type=MatchType.EXACT,
                code="cluster2",
                name="development",
            ),
        ],
        vlan_mappings=[
            VLANMapping(
                vid=100,
                name="Management",
                status="active",
                role="management",
                description="Management VLAN",
                tags=["prod"],
                vlan_group="Production VLANs",
            ),
            VLANMapping(
                vid=200,
                name="Application",
                status="active",
                role="application",
                description="Application VLAN",
                tags=["prod"],
                vlan_group="Production VLANs",
            ),
            VLANMapping(
                vid=300,
                name="Guest",
                status="active",
                description="Guest VLAN",
            ),
        ],
    )


@pytest.fixture
def org_config_minimal() -> OrganizationConfig:
    """Minimal organization config for testing without mappings."""
    return OrganizationConfig(
        site_mappings=[],
        environment_mappings=[],
        vlan_mappings=[],
    )


# ============================================================================
# Mapping Resolver Fixtures
# ============================================================================

@pytest.fixture
def mapping_resolver(org_config_with_mappings) -> MappingResolver:
    """MappingResolver configured with test mappings."""
    return MappingResolver(org_config_with_mappings)


@pytest.fixture
def mapping_resolver_empty() -> MappingResolver:
    """MappingResolver with no configured mappings."""
    return MappingResolver(OrganizationConfig())


# ============================================================================
# WinRM Mocking Fixtures
# ============================================================================

@pytest.fixture
def mock_winrm_session():
    """Mock WinRM Session for testing data collection."""
    session = MagicMock()
    
    # Default successful response
    session.run_ps.return_value = Mock(
        status_code=0,
        std_out=b'{}',  # Empty JSON for default
        std_err=b'',
    )
    
    return session


@pytest.fixture
def mock_winrm_session_with_data(mock_scvmm_data):
    """Mock WinRM Session with realistic SCVMM data response."""
    session = MagicMock()
    
    json_data = json.dumps(mock_scvmm_data).encode()
    session.run_ps.return_value = Mock(
        status_code=0,
        std_out=json_data,
        std_err=b'',
    )
    
    return session


@pytest.fixture
def mock_winrm_session_error():
    """Mock WinRM Session that returns an error."""
    session = MagicMock()
    
    session.run_ps.return_value = Mock(
        status_code=1,
        std_out=b'',
        std_err=b'PowerShell error: Command failed',
    )
    
    return session


@pytest.fixture
def mock_winrm_session_json_error():
    """Mock WinRM Session that returns invalid JSON."""
    session = MagicMock()
    
    session.run_ps.return_value = Mock(
        status_code=0,
        std_out=b'Invalid JSON {[}]',
        std_err=b'',
    )
    
    return session


# ============================================================================
# Entity Mocking Fixtures (for testing with mocked entity classes)
# ============================================================================

@pytest.fixture
def mock_entity_classes():
    """Mock entity classes for testing dependency injection."""
    return {
        "Entity": Mock(),
        "Cluster": Mock(),
        "VirtualMachine": Mock(),
        "VMInterface": Mock(),
        "VirtualDisk": Mock(),
        "Device": Mock(),
        "VLAN": Mock(return_value=Mock(vid=100, name="Test")),
        "IPAddress": Mock(),
    }


# ============================================================================
# Policy and Backend Mocking Fixtures
# ============================================================================

@pytest.fixture
def mock_policy():
    """Mock Policy object for testing backend.run()."""
    policy = Mock()
    policy.config = Mock()
    policy.config.model_dump = Mock(return_value={"package": "scvmm"})
    policy.scope = {
        "hostname": "test-scvmm.example.com",
        "username": "domain\\admin",
        "password": "password123",
        "organization_config": None,
    }
    return policy


@pytest.fixture
def mock_policy_with_org_config(org_config_with_mappings):
    """Mock Policy object with organization config."""
    policy = Mock()
    policy.config = Mock()
    policy.config.model_dump = Mock(return_value={"package": "scvmm"})
    policy.scope = {
        "hostname": "test-scvmm.example.com",
        "username": "domain\\admin",
        "password": "password123",
        "organization_config": org_config_with_mappings,
    }
    return policy


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def vlan_config_dict(org_config_with_mappings) -> Dict[int, Dict[str, Any]]:
    """VLAN configuration dictionary for testing."""
    return {
        vlan.vid: vlan.model_dump(exclude_none=True)
        for vlan in org_config_with_mappings.vlan_mappings
    }
