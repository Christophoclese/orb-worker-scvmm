"""Constants for SCVMM backend."""

# Map SCVMM VM status to NetBox VM status
# Reference: https://docs.microsoft.com/en-us/windows/win32/hyperv_v2/virtualmachinestate-enumeration
VM_STATUS_MAPPING = {
    # Active / running
    "Running": "Active",
    
    # Paused states
    "Paused": "Paused",
    "Pausing": "Paused",
    "PausePending": "Paused",
    "PauseCritical": "Paused",
    
    # Offline / stopped states
    "PowerOff": "Offline",
    "PoweringOff": "Offline",
    "Saved": "Offline",
    "Saving": "Offline",
    "Restoring": "Offline",
    "DiscardSavedState": "Offline",
    "DiscardingDrives": "Offline",
    "Reset": "Offline",
    
    # Transitional but otherwise healthy: Staged
    "Starting": "Staged",
    "MergingDrives": "Staged",
    "Deleting": "Staged",
    "CreatingCheckpoint": "Staged",
    "DeletingCheckpoint": "Staged",
    "RecoveringCheckpoint": "Staged",
    "InitializingCheckpointOperation": "Staged",
    "FinishingCheckpointOperation": "Staged",
    "UnderMigration": "Staged",
    "UnderReplacement": "Staged",
    "UnderLiveCloning": "Staged",
    
    # VM creation / template / update pipelines
    "UnderCreation": "Planned",
    "Stored": "Planned",
    "UnderTemplateCreation": "Planned",
    "UnderUpdate": "Planned",
    
    # Failure states
    "CreationFailed": "Failed",
    "TemplateCreationFailed": "Failed",
    "CustomizationFailed": "Failed",
    "UpdateFailed": "Failed",
    "MigrationFailed": "Failed",
    "ReplacementFailed": "Failed",
    "CheckpointFailed": "Failed",
    "ShieldingFailed": "Failed",
    "P2VCreationFailed": "Failed",
    "V2VCreationFailed": "Failed",
    
    # Missing / host issues / unsupported — treat as Failed
    "Missing": "Failed",
    "HostNotResponding": "Failed",
    "Unsupported": "Failed",
    "IncompleteVMConfig": "Failed",
    "UnsupportedSharedFiles": "Failed",
    "UnsupportedCluster": "Failed",
    
    # Database-only placeholder
    "DbOnly": "Failed",
}

# PowerShell script to collect SCVMM data
# Collects cluster information, VM configuration, virtual disks, network adapters, and IP addresses
SCVMM_DATA_COLLECTION_SCRIPT = """
$ErrorActionPreference = "Stop"
Import-Module -Name virtualmachinemanager
Get-VMMServer -ComputerName localhost | Out-Null

function Get-RootDisk {
    param($disk)

    if ($disk.ParentDisk -eq $null) {
        return $disk
    }
    else {
        # Recursively check the parent disk's parent
        return Get-RootDisk $disk.ParentDisk
    }
}

$Clusters = @()
$Clusters = Get-VMHostCluster |
    ForEach-Object {
        $names = foreach ($n in $_.Nodes) { [string]$n.Name }
        [pscustomobject]@{
        Name        = $_.Name.split('.')[0]
        ClusterName = $_.ClusterName
        DomainName  = $_.DomainName
        Description = $_.Description
        Hosts       = [string[]]$names
        }
    }

$VMS = @()
$VMs = Get-VM | ForEach-Object {
    $interfaces = @($_.VirtualNetworkAdapters | ForEach-Object {
        $name = "Network Adapter " + ([int]$_.SlotId + 1)
        If ($_.VLanEnabled) {
            $mode = "access"
            $untagged_vlan = [int]$_.VLanId
        }
        Else {
            $mode = $null
            $untagged_vlan = $null
        }
        [pscustomobject]@{
            Name = $name
            MacAddress = $_.MacAddress
            Enabled = [System.Convert]::ToBoolean($_.Enabled)
            Mode = $mode
            UntaggedVlan = $untagged_vlan
            IPv4Addresses = $_.IPv4Addresses
            IPv4Subnets = $_.IPv4Subnets
        }
    })
    $disks = @($_.VirtualHardDisks | ForEach-Object {
        $rootDisk = Get-RootDisk $_
        [pscustomobject]@{
            Name = $rootDisk.Name
            VHDFormatType = $rootDisk.VHDFormatType.ToString()
            Size = [int]($rootDisk.MaximumSize / 1MB)
        }
    })
    [pscustomobject]@{
        Name = $_.Name
        Description = $_.Description
        CPUCount = $_.CPUCount
        # Convert to MB in base 10, which is what NetBox expects
        Memory = [int]($_.Memory * 1000 / 1024)
        OperatingSystem = $_.OperatingSystem
        Status = $_.Status.ToString()
        HostName = $_.VMHost.Name
        ClusterName = $_.VMHost.HostCluster.ClusterName
        Interfaces = $interfaces
        Disks = $disks
    }
}
$Data = @{
    Clusters = $Clusters
    VMs = $VMs
}
$Data | ConvertTo-Json -Depth 5
"""
