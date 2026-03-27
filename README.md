# orb-worker-scvmm

This is a custom worker for the NetBoxLabs Orb Agent designed to collect Cluster and VM information from a Microsoft System Center Virtual Machine Manager (SCVMM) instance.

This worker is designed to use WinRM to perform a connection to an SCVMM server which has the PowerShell Module `virtualmachinemanager` available. Using this remote connection, an attempt to connect to the SCVMM server on localhost occurs, then cluster and VM data are gathered and returned as JSON for processing into Diode entities.

The following NetBox entities may be created or updated from the SCVMM data:

- Clusters
- Virtual Machines
- VM Disks
- VM Interfaces
- IP Addresses (from VM interfaces)
- MAC Addresses (from VM interfaces)
- VLANs (from VM network adapter VLAN IDs)

## Requirements

- [netboxlabs/diode](https://github.com/netboxlabs/diode) running and accessible to the orb-agent
- [netboxlabs/orb-agent](https://github.com/netboxlabs/orb-agent) installed and able to communicate with Diode
- A user account with WinRM access *and* read permissions in SCVMM
- WinRM access to SCVMM server with `virtualmachinemanager` PowerShell Module installed

## Usage

1. Follow the [orb-agent documentation](https://github.com/netboxlabs/orb-agent/blob/develop/docs/config_samples.md#custom-workers) to configure `workers.txt` or similar file.
2. Create an Orb configuration file (example for `scvmm-infra.internal.example.com`):
```yaml
orb:
  config_manager:
    active: local

  backends:
    worker:
    common:
      diode:
        target: grpc://netbox.example.com:8080/diode
        client_id: ${DIODE_CLIENT_ID}
        client_secret: ${DIODE_CLIENT_SECRET}
        agent_name: scvmm-worker

  policies:
    worker:
      scvmm-infrastructure:
        config:
          package: scvmm
        scope:
          hostname: scvmm-infra.internal.example.com
          username: ${SCVMM_USERNAME}
          password: ${SCVMM_PASSWORD}
          organization_config:
            site_mappings:
            - code: "hq"
              name: "Headquarters"
              match_type: "prefix"
            - code: "boi"
              name: "Boise"
              match_type: "prefix"
            default_site: "Undefined"
            environment_mappings:
            - code: "prd"
              name: "Production Clusters"
              match_type: "prefix"
            - code: "dev"
              name: "Development Clusters"
              match_type: "prefix"
            default_group: "Undefined"
            vlan_mappings:
            - vid: 100
              name: "VOIP"
              description: "Voice VLAN"
            - vid: 200
              name: "Data"
              description: "Data VLAN"
```
3. Ensure environment variables are set for `${DIODE_CLIENT_ID}`, `${DIODE_CLIENT_SECRET}`, `${SCVMM_USERNAME}`, and `${SCVMM_PASSWORD}`.
4. Set the Diode branch in NetBox as needed.
5. Start the Orb Agent and monitor logs for successful data collection. Example: `docker run --net=host -v ${PWD}:/opt/orb/ -v /etc/ssl/certs:/etc/ssl/certs:ro -e DIODE_CLIENT_ID -e DIODE_CLIENT_SECRET -e SCVMM_USERNAME -e SCVMM_PASSWORD -e INSTALL_WORKERS_PATH=/opt/orb/workers.txt netboxlabs/orb-agent:develop run -c /opt/orb/scvmm.yml`

## Configuration

The worker supports the following configuration parameters:

- `hostname` (string, required): The hostname or IP address of the SCVMM server to connect to.
- `username` (string, required): The username for WinRM & SCVMM authentication.
- `password` (string, required): The password for WinRM & SCVMM authentication.
- `winrm_config` (object, optional): Custom WinRM connection parameters (port, protocol, transport, path, cert validation).
- `organization_config` (object, optional): Mappings for site and environment classification, as well as VLAN ID to NetBox attribute mappings. Supports exact, prefix, and regex matching for cluster names.

See the [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for detailed configuration instructions and examples.

## Testing

This project includes comprehensive test coverage with a target of **80%+ code coverage**. Tests use mocking to avoid requiring actual WinRM connections or SCVMM infrastructure.

**Quick Start:**
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=scvmm --cov-report=html --cov-report=term-missing

# Run specific test file or pattern
pytest tests/test_entity_creation.py -v
pytest tests/ -k "vlan" -v
```

For detailed testing patterns, best practices, mocking strategies, fixture documentation, and contribution guidelines, see [DEVELOPMENT.md](DEVELOPMENT.md).
