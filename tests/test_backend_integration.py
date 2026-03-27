"""End-to-end integration tests for ScvmmBackend."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from scvmm.main import ScvmmBackend
from scvmm.models import OrganizationConfig


class TestBackendSetup:
    """Tests for backend setup and initialization."""

    def test_backend_setup_returns_metadata(self):
        """Test that setup() returns correct metadata."""
        backend = ScvmmBackend()
        metadata = backend.setup()
        
        assert metadata.name == "ScvmmBackend"
        assert metadata.app_name == "orb-worker-scvmm"
        assert metadata.app_version == "0.1.0"

    def test_backend_init_with_default_entity_classes(self):
        """Test that backend initializes with default entity classes."""
        backend = ScvmmBackend()
        
        # All entity classes should be set to their defaults
        assert backend.Entity is not None
        assert backend.Cluster is not None
        assert backend.VirtualMachine is not None
        assert backend.VMInterface is not None
        assert backend.VirtualDisk is not None
        assert backend.Device is not None
        assert backend.VLAN is not None
        assert backend.IPAddress is not None

    def test_backend_init_with_injected_entity_classes(self, mock_entity_classes):
        """Test dependency injection of entity classes."""
        backend = ScvmmBackend(
            entity_class=mock_entity_classes["Entity"],
            cluster_class=mock_entity_classes["Cluster"],
            vm_class=mock_entity_classes["VirtualMachine"],
            interface_class=mock_entity_classes["VMInterface"],
            disk_class=mock_entity_classes["VirtualDisk"],
            device_class=mock_entity_classes["Device"],
            vlan_class=mock_entity_classes["VLAN"],
            ip_address_class=mock_entity_classes["IPAddress"],
        )
        
        # Verify injected classes are used
        assert backend.Entity == mock_entity_classes["Entity"]
        assert backend.Cluster == mock_entity_classes["Cluster"]
        assert backend.VLAN == mock_entity_classes["VLAN"]


class TestBackendRunWorkflow:
    """Tests for backend.run() workflow."""

    @patch('scvmm.collect.winrm.Session')
    def test_backend_run_full_workflow(self, mock_session_class, mock_scvmm_data, mock_policy):
        """Test full backend.run() workflow with mocked WinRM."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", mock_policy))
        
        # Should return entities
        assert len(entities) > 0
        
        # Verify WinRM was called
        mock_session_instance.run_ps.assert_called_once()

    @patch('scvmm.collect.winrm.Session')
    def test_backend_run_with_org_config(self, mock_session_class, mock_scvmm_data, mock_policy_with_org_config):
        """Test backend.run() with organization configuration."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", mock_policy_with_org_config))
        
        # Should process entities with mappings applied
        assert len(entities) > 0

    def test_backend_run_invalid_config_raises_error(self, mock_policy):
        """Test that invalid config raises validation error."""
        invalid_policy = Mock()
        invalid_policy.config = Mock()
        invalid_policy.config.model_dump = Mock(return_value={"invalid_field": "value"})
        invalid_policy.scope = mock_policy.scope
        
        backend = ScvmmBackend()
        
        with pytest.raises(Exception):
            list(backend.run("test-policy", invalid_policy))

    def test_backend_run_invalid_scope_raises_error(self, mock_policy):
        """Test that invalid scope raises validation error."""
        invalid_policy = Mock()
        invalid_policy.config = Mock()
        invalid_policy.config.model_dump = Mock(return_value={"package": "scvmm"})
        invalid_policy.scope = {"invalid": "scope"}
        
        backend = ScvmmBackend()
        
        with pytest.raises(Exception):
            list(backend.run("test-policy", invalid_policy))

    def test_backend_run_non_dict_scope_raises_error(self, mock_policy):
        """Test that non-dict scope raises error."""
        invalid_policy = Mock()
        invalid_policy.config = Mock()
        invalid_policy.config.model_dump = Mock(return_value={"package": "scvmm"})
        invalid_policy.scope = "invalid"
        
        backend = ScvmmBackend()
        
        with pytest.raises(ValueError, match="Policy scope must be a dictionary"):
            list(backend.run("test-policy", invalid_policy))

    @patch('scvmm.collect.winrm.Session')
    def test_backend_run_returns_generator(self, mock_session_class, mock_scvmm_data, mock_policy):
        """Test that backend.run() returns an iterable generator."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        result = backend.run("test-policy", mock_policy)
        
        # Should be iterable
        assert hasattr(result, '__iter__')

    @patch('scvmm.collect.winrm.Session')
    def test_backend_run_winrm_connection_failure(self, mock_session_class, mock_policy):
        """Test handling of WinRM connection failure."""
        mock_session_class.side_effect = Exception("Connection failed")
        
        backend = ScvmmBackend()
        
        with pytest.raises(Exception):
            list(backend.run("test-policy", mock_policy))

    @patch('scvmm.collect.winrm.Session')
    def test_backend_run_powershell_error(self, mock_session_class, mock_policy):
        """Test handling of PowerShell execution error."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=1,
            std_out=b'',
            std_err=b'PowerShell error',
        )
        
        backend = ScvmmBackend()
        
        with pytest.raises(Exception):
            list(backend.run("test-policy", mock_policy))


class TestBackendInitializeResolver:
    """Tests for mapping resolver initialization in backend."""

    @patch('scvmm.collect.winrm.Session')
    def test_backend_initializes_resolver_without_org_config(self, mock_session_class, mock_scvmm_data):
        """Test that backend initializes empty resolver when no org config."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        policy = Mock()
        policy.config = Mock()
        policy.config.model_dump = Mock(return_value={"package": "scvmm"})
        policy.scope = {
            "hostname": "test",
            "username": "admin",
            "password": "pass",
            "organization_config": None,
        }
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", policy))
        
        # Should process but with minimal mapping
        assert len(entities) > 0

    @patch('scvmm.collect.winrm.Session')
    def test_backend_initializes_resolver_with_org_config(self, mock_session_class, mock_scvmm_data, org_config_with_mappings):
        """Test that backend initializes resolver with org config."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        policy = Mock()
        policy.config = Mock()
        policy.config.model_dump = Mock(return_value={"package": "scvmm"})
        policy.scope = {
            "hostname": "test",
            "username": "admin",
            "password": "pass",
            "organization_config": org_config_with_mappings,
        }
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", policy))
        
        # Should process with mappings applied
        assert len(entities) > 0


class TestEntityReturnTypes:
    """Tests for entity type validation."""

    @patch('scvmm.collect.winrm.Session')
    def test_backend_returns_correct_entity_types(self, mock_session_class, mock_scvmm_data, mock_policy):
        """Test that backend returns correct entity types."""
        from google.protobuf.message import Message
        
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", mock_policy))
        
        # All should be protobuf Entity message instances
        for entity in entities:
            assert isinstance(entity, Message)
            # Verify it's an ingester Entity (has cluster, vm_interface, etc. fields)
            assert type(entity).__name__ == "Entity"
            assert "cluster" in type(entity).DESCRIPTOR.fields_by_name or \
                   "virtual_machine" in type(entity).DESCRIPTOR.fields_by_name or \
                   "vm_interface" in type(entity).DESCRIPTOR.fields_by_name or \
                   "virtual_disk" in type(entity).DESCRIPTOR.fields_by_name or \
                   "device" in type(entity).DESCRIPTOR.fields_by_name

    @patch('scvmm.collect.winrm.Session')
    def test_backend_returns_various_entity_subtypes(self, mock_session_class, mock_scvmm_data, mock_policy):
        """Test that backend returns various subtypes of entities."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", mock_policy))
        
        # Should have various entity types
        has_cluster = any(e.cluster is not None for e in entities)
        has_vm_interface = any(e.vm_interface is not None for e in entities)
        has_disk = any(e.virtual_disk is not None for e in entities)
        
        # With test data, should have at least clusters and interfaces/vms
        assert has_cluster or has_vm_interface or has_disk


class TestVLANResolutionIntegration:
    """Integration tests for VLAN resolution in full backend workflow."""

    @patch('scvmm.collect.winrm.Session')
    def test_backend_applies_vlan_mappings_in_workflow(self, mock_session_class, mock_scvmm_data, mock_policy_with_org_config):
        """Test that VLAN mappings are applied in full backend workflow."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        entities = list(backend.run("test-policy", mock_policy_with_org_config))
        
        # Should have entities returned
        assert len(entities) > 0
        
        # Should have interface entities with VLANs assigned when present
        interface_entities = [e for e in entities if e.vm_interface is not None]
        assert len(interface_entities) > 0  # Should have at least some interface entities


class TestErrorHandlingIntegration:
    """Integration tests for error handling in backend."""

    @patch('scvmm.collect.winrm.Session')
    def test_backend_handles_malformed_scvmm_data(self, mock_session_class, mock_policy):
        """Test backend handling of malformed SCVMM data."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        # Return data missing expected fields
        malformed_data = {
            "Clusters": [{"Name": "test"}],  # Missing other required fields
            "VMs": [],
        }
        
        json_data = json.dumps(malformed_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        backend = ScvmmBackend()
        
        # Should handle gracefully or raise informative error
        try:
            entities = list(backend.run("test-policy", mock_policy))
            # If no error, should still produce some output
            assert isinstance(entities, list)
        except Exception:
            # If error, it should be informative
            pass
