#!/usr/bin/env python

import logging
from collections.abc import Iterable
from typing import Optional

from netboxlabs.diode.sdk.ingester import (
    Cluster,
    VirtualMachine,
    VMInterface,
    VirtualDisk,
    Device,
    Entity,
    VLAN,
    IPAddress,
)
from pydantic import BaseModel, Field, ValidationError

from worker.backend import Backend
from worker.models import Metadata, Policy

from scvmm.collect import collect_scvmm_data
from scvmm.models import WinRMConfig, OrganizationConfig
from scvmm.mapping import MappingResolver
from scvmm.constants import VM_STATUS_MAPPING

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config(BaseModel):
    """Validation model for config field."""

    package: str = Field(..., description="Package name")
    #custom: str = Field(..., description="Custom field, can be of any type")

class ScopeMap(BaseModel):
    """Validation model for scope map field."""

    hostname: str = Field(..., description="Hostname of the scvmm server")
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password for authentication")
    winrm_config: Optional[WinRMConfig] = Field(
        default=None, description="Optional WinRM connection configuration"
    )
    organization_config: Optional[OrganizationConfig] = Field(
        default=None, description="Optional organization-specific naming and mapping configuration"
    )

class ScvmmBackend(Backend):
    """Scvmm backend implementation."""

    def __init__(self, **kwargs):
        """Initialize ScvmmBackend with optional dependency injection for entity classes.
        
        Allows optional injection of entity classes for testing purposes.
        All parameters default to real NetBox entity classes for production use.
        """
        super().__init__()
        # Optional DI: allow tests to inject mock entity classes
        self.Entity = kwargs.get('entity_class', Entity)
        self.Cluster = kwargs.get('cluster_class', Cluster)
        self.VirtualMachine = kwargs.get('vm_class', VirtualMachine)
        self.VMInterface = kwargs.get('interface_class', VMInterface)
        self.VirtualDisk = kwargs.get('disk_class', VirtualDisk)
        self.Device = kwargs.get('device_class', Device)
        self.VLAN = kwargs.get('vlan_class', VLAN)
        self.IPAddress = kwargs.get('ip_address_class', IPAddress)

    def setup(self) -> Metadata:
        #logger.info("Setting up ScvmmBackend with configuration: %s", self.config)

        return Metadata(
            name="ScvmmBackend",
            app_name="orb-worker-scvmm",
            app_version="0.1.0",
        )

    def run(self, policy_name: str, policy: Policy) -> Iterable[Entity]:
        logger.info(f"Running ScvmmBackend with policy: {policy_name}")

        # Read policy config
        try:
            config = Config(**policy.config.model_dump())
            logger.info(f"Parsed policy configuration: {config}")
        except ValidationError as e:
            logger.error(f"Policy configuration validation error: {e}")
            raise

        # Read policy scope
        if isinstance(policy.scope, dict):
            try:
                scope = ScopeMap(**policy.scope)
                # Don't output whole scope, it has passwords!
                #logger.info(f"Parsed policy scope: {scope}")
            except ValidationError as e:
                logger.error(f"Policy scope validation error: {e}")
                raise
        else:
            logger.error("Policy scope is not a valid dictionary")
            raise ValueError("Policy scope must be a dictionary")

        # Initialize mapping resolver from organization config
        if scope.organization_config:
            resolver = MappingResolver(scope.organization_config)
            logger.info("Using organization-specific site and environment mappings")
        else:
            resolver = MappingResolver()
            logger.warning(
                "No organization config provided, consider providing organization_config for org-specific mappings."
            )

        # Call function to winrm into scvmm server and retrieve data, then create entities based on that data
        data = collect_scvmm_data(
            scope.hostname, scope.username, scope.password, scope.winrm_config
        )
        entities = self.create_entities_from_data(data, resolver, scope.organization_config)

        return entities

    def create_entities_from_data(self, data, resolver: MappingResolver, organization_config: Optional[OrganizationConfig] = None):
        logger.info("Begin processing SCVMM data.")

        # Build VLAN lookup dict for fast access by VID
        vlan_config_dict = {}
        if organization_config and organization_config.vlan_mappings:
            vlan_config_dict = {
                vlan.vid: vlan.model_dump(exclude_none=True)
                for vlan in organization_config.vlan_mappings
            }
            logger.info(f"Loaded {len(vlan_config_dict)} VLAN mappings from organization config")

        entities = []

        for cluster in data.get("Clusters", []):
            logger.info(f"Working on cluster: {cluster['Name']}")
            entities.append(Entity(cluster=Cluster(
                name=cluster["Name"],
                type="Hyper-V",
                status="active",
                description=cluster.get("Description", ""),
                group=resolver.resolve_group(cluster["Name"]),
                scope_site=resolver.resolve_site(cluster["Name"]),
            )))

            # Try to add nodes as devices under the cluster
            # Will not successfully create missing devices in NetBox since we don't know details like device type
            # TODO: Consider adding a config option to allow mapping device properties for cluster nodes, for example supplying custom values for required fields like device role, or modifying how the name is returned
            for node in cluster.get("Hosts", []):
                logger.info(f"Attempting to add node '{node}' as device under cluster '{cluster['Name']}'")
                entities.append(Entity(device=Device(
                    name=node.split('.')[0],  # Use the hostname without domain as device name
                    role="Hyper-V Host",
                    status="active",
                    cluster=cluster["Name"],
                )))

        for vm in data.get("VMs", []):
            logger.info(f"Working on VM: {vm['Name']}")
            vm_args = {
                "name": vm["Name"],
                "status": self.get_status_for_vm(vm["Status"], vm["Name"]),
                "vcpus": vm.get("CPUCount", 0),
                "memory": vm.get("Memory", 0),
            }

            if len(vm.get("Description", "")) > 200:
                logger.warning(f"Description for VM '{vm['Name']}' is too long for NetBox (max 200 chars), truncating.")
                vm_args["description"] = vm.get("Description", "")[:200]

            if vm.get("ClusterName", "") != "" and vm.get("ClusterName") is not None:
                vm_args["cluster"] = Cluster(
                    name=vm.get("ClusterName"),
                    type="Hyper-V",
                    status="active",
                    group=resolver.resolve_group(vm.get("ClusterName")),
                )
            else:
                vm_args["device"] = vm.get("HostName", "").split('.')[0]  # Use the hostname without domain as device name

            # If this VM has exactly one interface with exactly one IP address, assign it as primary_ip4
            interfaces = vm.get("Interfaces", [])
            if len(interfaces) == 1:
                single_interface = interfaces[0]
                ipv4_addresses = single_interface.get("IPv4Addresses", [])
                if len(ipv4_addresses) == 1:
                    ip_addr = ipv4_addresses[0]
                    ipv4_subnets = single_interface.get("IPv4Subnets", [])
                    subnet = ipv4_subnets[0] if ipv4_subnets else "/32"
                    cidr = subnet.split('/')[1] if '/' in subnet else '32'
                    vm_args["primary_ip4"] = f"{ip_addr}/{cidr}"
                    logger.info(f"Assigning {vm_args['primary_ip4']} as primary IPv4 for VM {vm['Name']}")

            logger.info(f"Working on VM NICs")
            for interface in vm.get("Interfaces", []):
                logger.info(f"Working on NIC: {interface['Name']} on {vm['Name']}")
                nic_args = {
                    "virtual_machine": VirtualMachine(**vm_args),
                    "name": interface["Name"],
                    "primary_mac_address": interface.get("MacAddress", ""),
                    "enabled": interface.get("Enabled", False),
                }

                if interface.get("Mode", None) is not None and interface.get("UntaggedVlan", None) is not None:
                    nic_args["mode"] = interface.get("Mode")

                    # Look up VLAN configuration
                    vlan_id = interface.get("UntaggedVlan")
                    vlan_config = self._get_vlan_config(vlan_config_dict, vlan_id)

                    # Build VLAN entity from config or defaults
                    nic_args["untagged_vlan"] = self._build_vlan_entity(vlan_id, vlan_config)
                else:
                    nic_args["untagged_vlan"] = None

                # If this interface has IP addresses, we need to create IPAddress entities for them and link them to the VMInterface
                # Otherwise, we can just create the VMInterface without an IP address
                if interface.get("IPv4Addresses", []):
                    for ip, subnet in zip(interface.get("IPv4Addresses", []), interface.get("IPv4Subnets", [])):
                        cidr = subnet.split('/')[1] if '/' in subnet else '32'  # Default to /32 if no subnet is provided
                        entities.append(Entity(ip_address=IPAddress(
                            assigned_object_vm_interface=VMInterface(**nic_args),
                            address=f"{ip}/{cidr}",
                            status="active",
                        )))
                else:
                    entities.append(Entity(vm_interface=VMInterface(**nic_args)))

            logger.info(f"Working on VM Disks")
            for disk in vm.get("Disks", []):
                logger.info(f"Working on Disk: {disk['Name']} on {vm['Name']}")
                disk_args = {
                    "virtual_machine": VirtualMachine(**vm_args),
                    "size": disk.get("Size", 0),
                }
                
                disk_args["name"] = disk["Name"] + "." + disk.get("VHDFormatType", "vhdx")

                if len(disk_args["name"]) > 64:
                    logger.warning(f"Disk name '{disk_args['name']}' is too long for NetBox (max 64 chars), truncating.")
                    disk_args["name"] = disk_args["name"][:64]

                entities.append(Entity(virtual_disk=VirtualDisk(**disk_args)))

        return entities

    def _build_vlan_entity(self, vlan_id: int, vlan_config: Optional[dict]) -> VLAN:
        """Build a VLAN entity from configuration.
        
        Args:
            vlan_id: VLAN ID (VID)
            vlan_config: Optional dictionary of VLAN configuration from OrganizationConfig.vlan_mappings
        
        Returns:
            VLAN entity object
        
        Raises:
            TypeError: If VLAN model doesn't support optional attributes (with fallback to basic fields)
        """
        vlan_kwargs = {
            "vid": vlan_id,
            "name": vlan_config.get("name") if vlan_config else str(vlan_id),
            "status": vlan_config.get("status", "active") if vlan_config else "active",
        }

        # Apply optional VLAN attributes if config exists and supports them
        if vlan_config:
            if "role" in vlan_config and vlan_config["role"]:
                vlan_kwargs["role"] = vlan_config["role"]
            if "description" in vlan_config and vlan_config["description"]:
                vlan_kwargs["description"] = vlan_config["description"]
            if "tags" in vlan_config and vlan_config["tags"]:
                vlan_kwargs["tags"] = vlan_config["tags"]
            if "vlan_group" in vlan_config and vlan_config["vlan_group"]:
                vlan_kwargs["group"] = vlan_config["vlan_group"]

        return self.VLAN(**vlan_kwargs)

    def _get_vlan_config(self, vlan_config_dict: dict, vid: int) -> Optional[dict]:
        """Look up VLAN configuration by VID.

        Args:
            vlan_config_dict: Dictionary of VLAN configurations keyed by VID
            vid: VLAN ID to look up

        Returns:
            VLAN config dict if found, None otherwise
        """
        return vlan_config_dict.get(vid)

    def get_status_for_vm(self, vm_status, vm_name):
        """Map SCVMM VM status to NetBox VM status.
        
        Args:
            vm_status: SCVMM VM status string
            vm_name: Name of the VM (for logging)
        
        Returns:
            Lowercase NetBox status (e.g., 'active', 'offline', 'failed')
        
        TODO: Consider making this mapping configurable in case users want to handle 
        certain states differently, for example treating "Saved" as "Planned" instead of "Offline"
        """
        if vm_status not in VM_STATUS_MAPPING:
            logger.warning(f"Unknown VM status '{vm_status}' encountered on '{vm_name}', defaulting to 'Offline'")
            status = "Offline"
        else:
            status = VM_STATUS_MAPPING[vm_status]

        return status.lower()

def main():
    print("Hello from orb-worker-scvmm!")


if __name__ == "__main__":
    main()
