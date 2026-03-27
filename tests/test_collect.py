"""Tests for SCVMM data collection via WinRM."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from scvmm.collect import collect_scvmm_data
from scvmm.constants import SCVMM_DATA_COLLECTION_SCRIPT


class TestCollectScvmmData:
    """Tests for collect_scvmm_data function."""

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_success(self, mock_session_class, mock_scvmm_data):
        """Test successful data collection from SCVMM."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        json_data = json.dumps(mock_scvmm_data).encode()
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        result = collect_scvmm_data(
            hostname="scvmm.example.com",
            username="domain\\admin",
            password="password123",
        )
        
        assert result == mock_scvmm_data
        assert "Clusters" in result
        assert "VMs" in result

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_connection_error(self, mock_session_class):
        """Test handling of WinRM connection errors."""
        mock_session_class.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            collect_scvmm_data(
                hostname="invalid.example.com",
                username="domain\\admin",
                password="password",
            )

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_powershell_error(self, mock_session_class):
        """Test handling of PowerShell script execution errors."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=1,
            std_out=b'',
            std_err=b'PowerShell error: Get-VM not found',
        )
        
        with pytest.raises(Exception, match="PowerShell script execution failed"):
            collect_scvmm_data(
                hostname="scvmm.example.com",
                username="domain\\admin",
                password="password",
            )

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_json_parse_error(self, mock_session_class):
        """Test handling of invalid JSON response."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=b'Invalid JSON {[}]',
            std_err=b'',
        )
        
        with pytest.raises(Exception):
            collect_scvmm_data(
                hostname="scvmm.example.com",
                username="domain\\admin",
                password="password",
            )

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_uses_correct_credentials(self, mock_session_class):
        """Test that WinRM session uses provided credentials."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=b'{"Clusters":[],"VMs":[]}',
            std_err=b'',
        )
        
        collect_scvmm_data(
            hostname="scvmm.example.com",
            username="domain\\testuser",
            password="testpass123",
        )
        
        # Verify Session was called with correct auth tuple
        mock_session_class.assert_called_once()
        call_args = mock_session_class.call_args
        assert call_args[1]["auth"] == ("domain\\testuser", "testpass123")

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_uses_default_winrm_config(self, mock_session_class):
        """Test that default WinRM config is used when not provided."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=b'{"Clusters":[],"VMs":[]}',
            std_err=b'',
        )
        
        collect_scvmm_data(
            hostname="scvmm.example.com",
            username="admin",
            password="pass",
        )
        
        # Verify default URL and transport
        call_args = mock_session_class.call_args
        assert call_args[0][0] == "http://scvmm.example.com:5985/wsman"
        assert call_args[1]["transport"] == "ntlm"

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_uses_custom_winrm_config(self, mock_session_class):
        """Test that custom WinRM config is used when provided."""
        from scvmm.models import WinRMConfig
        
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=b'{"Clusters":[],"VMs":[]}',
            std_err=b'',
        )
        
        custom_config = WinRMConfig(
            protocol="https",
            port=5986,
            path="/custom/wsman",
            transport="kerberos",
        )
        
        collect_scvmm_data(
            hostname="scvmm.example.com",
            username="admin",
            password="pass",
            winrm_config=custom_config,
        )
        
        # Verify custom config was used
        call_args = mock_session_class.call_args
        assert call_args[0][0] == "https://scvmm.example.com:5986/custom/wsman"
        assert call_args[1]["transport"] == "kerberos"

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_utf8_decoding(self, mock_session_class, mock_scvmm_data):
        """Test that response is correctly decoded as UTF-8."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        # Create JSON with UTF-8 characters
        data_with_unicode = mock_scvmm_data.copy()
        data_with_unicode["Clusters"][0]["Description"] = "Test with Unicode: café"
        
        json_data = json.dumps(data_with_unicode).encode('utf-8')
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=json_data,
            std_err=b'',
        )
        
        result = collect_scvmm_data(
            hostname="scvmm.example.com",
            username="admin",
            password="pass",
        )
        
        assert "café" in result["Clusters"][0]["Description"]

    @patch('scvmm.collect.winrm.Session')
    def test_collect_scvmm_data_calls_run_ps_with_script(self, mock_session_class):
        """Test that PowerShell script is executed via run_ps."""
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance
        
        mock_session_instance.run_ps.return_value = Mock(
            status_code=0,
            std_out=b'{"Clusters":[],"VMs":[]}',
            std_err=b'',
        )
        
        collect_scvmm_data(
            hostname="scvmm.example.com",
            username="admin",
            password="pass",
        )
        
        # Verify run_ps was called with the script constant
        mock_session_instance.run_ps.assert_called_once()
        script_arg = mock_session_instance.run_ps.call_args[0][0]
        assert "$ErrorActionPreference" in script_arg
        assert "Get-VMHostCluster" in script_arg
        assert "Get-VM" in script_arg


class TestPowerShellScript:
    """Tests for PowerShell script constant."""

    def test_script_constant_exists(self):
        """Test that PowerShell script constant is defined."""
        assert SCVMM_DATA_COLLECTION_SCRIPT is not None
        assert len(SCVMM_DATA_COLLECTION_SCRIPT) > 0

    def test_script_has_error_handling(self):
        """Test that script has proper error handling."""
        assert "$ErrorActionPreference = \"Stop\"" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_imports_virtualmachinemanager(self):
        """Test that script imports required VMM module."""
        assert "Import-Module -Name virtualmachinemanager" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_gets_clusters(self):
        """Test that script calls Get-VMHostCluster."""
        assert "Get-VMHostCluster" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_gets_vms(self):
        """Test that script calls Get-VM."""
        assert "Get-VM" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_collects_interfaces(self):
        """Test that script collects network adapter info."""
        assert "VirtualNetworkAdapters" in SCVMM_DATA_COLLECTION_SCRIPT
        assert "VLanId" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_collects_disks(self):
        """Test that script collects virtual disk info."""
        assert "VirtualHardDisks" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_outputs_json(self):
        """Test that script outputs JSON format."""
        assert "ConvertTo-Json" in SCVMM_DATA_COLLECTION_SCRIPT

    def test_script_handles_ipv4_addresses(self):
        """Test that script collects IPv4 address information."""
        assert "IPv4Addresses" in SCVMM_DATA_COLLECTION_SCRIPT
        assert "IPv4Subnets" in SCVMM_DATA_COLLECTION_SCRIPT
