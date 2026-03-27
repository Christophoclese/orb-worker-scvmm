# Quick Start: Configuring orb-worker-scvmm

## Overview

This guide provides step-by-step instructions for configuring the `orb-worker-scvmm` worker to discover SCVMM clusters, hosts, and VMs, and transform them into Orb entities. The worker is highly customizable via policy scope configuration, allowing you to define site mappings, environment mappings, VLAN mappings, and WinRM connection parameters.

## Basic Usage

### Minimal Configuration (Default Behavior)

If you only provide hostname, username, and password, the worker uses built-in defaults:

```yaml
hostname: scvmm-server.example.com
username: domainuser
password: password123
```

**Result**: Uses HTTP port 5985, NTLM authentication, and built-in site/environment mappings.

### Custom Site & Environment Mappings

Define how cluster names map to physical sites and environments:

```yaml
hostname: scvmm-server.example.com
username: domainuser
password: password123
organization_config:
  site_mappings:
    - code: boi
      name: Boise
      match_type: prefix
    - code: ptl
      name: Portland
      match_type: prefix
    - code: hq
      name: Headquarters
      match_type: prefix
  environment_mappings:
    - code: prd
      name: Production
      match_type: prefix
    - code: dev
      name: Development
      match_type: prefix
    - code: inf
      name: Infrastructure
      match_type: prefix
```

**Result**:

- Cluster "boi-prod-01" → Site: "Boise", Env: "Production"
- Cluster "ptl-dev-01" → Site: "Portland", Env: "Development"
- Cluster "hq-inf-01" → Site: "Headquarters", Env: "Infrastructure"

## Matching Strategies

### Prefix Match (Default)

Checks if the code appears anywhere in the cluster name (case-insensitive):

```yaml
code: boi
name: Boise
match_type: prefix
```

Matches: `boi-cluster`, `BOI-CLUSTER`, `cluster-boi-01`

### Exact Match

Requires the entire cluster name to match exactly (case-insensitive):

```yaml
code: cluster-production
name: Production
match_type: exact
```

Matches: `cluster-production` (exact only)

### Regex Match

Uses regular expression patterns for complex matching:

```yaml
code: ^cluster-[a-z]+-\d{2}$
name: Corporate
match_type: regex
```

Matches: `cluster-boi-01`, `cluster-ptl-99`

## Advanced: Custom WinRM Settings

If your SCVMM server uses HTTPS or non-standard settings:

```yaml
hostname: scvmm.example.com
username: admin@domain.com
password: secret
winrm_config:
  port: 5986
  protocol: https
  path: /wsman
  transport: kerberos
  server_certificate_validation: validate
organization_config:
  site_mappings: [...]
  environment_mappings: [...]
```

**WinRM Config Fields:**

- **port**: 1-65535 (default: 5985 for HTTP, 5986 for HTTPS)
- **protocol**: "http" or "https" (default: "http")
- **path**: WinRM endpoint path (default: "/wsman")
- **transport**: "ntlm", "kerberos", "basic", "certificate" (default: "ntlm")
- **server_certificate_validation**: "ignore", "validate", "self-signed" (default: "ignore")

## VLAN Mapping Configuration

Map VLAN IDs discovered in SCVMM to NetBox VLAN attributes. When a VLAN ID from SCVMM matches a configured mapping, all specified attributes will be applied to the VLAN in NetBox.

### Basic VLAN Mapping

The simplest configuration requires only a VLAN ID and Name:

```yaml
organization_config:
  vlan_mappings:
    - vid: 100
      name: Management
    - vid: 200
      name: Production
    - vid: 300
      name: Development
```

**Result**:

- VLAN 100 will be created in NetBox as "Management" with Status: "Active"
- VLAN 200 will be created in NetBox as "Production" with Status: "Active"
- VLAN 300 will be created in NetBox as "Development" with Status: "Active"
- Any other VLAN IDs found in SCVMM will use the VLAN ID as the name with Status: "Active"

### Full VLAN Mapping Example

You can also specify optional attributes like role, description, tags, and VLAN Group:

```yaml
organization_config:
  vlan_mappings:
    - vid: 100
      name: Management
      status: active
      description: Out-of-band management network
      role: management
    - vid: 200
      name: Production
      status: active
      role: production
      description: Production workload network
      tags:
        - prod
        - monitored
    - vid: 300
      name: Development
      status: planned
      role: development
      description: Development workload network
      tags:
        - dev
      vlan_group: AppVLANs
    - vid: 400
      name: Guest
```

**VLAN Mapping Fields:**

- **vid** (required): VLAN ID integer (1-4094+)
- **name** (required): NetBox VLAN name/description
- **status** (optional): NetBox VLAN status - "active", "planned", or "deprecated" (defaults to "active")
- **role** (optional): NetBox VLAN role (e.g., "management", "production", "development")
- **description** (optional): Additional description for the VLAN
- **tags** (optional): List of NetBox tag names to apply to this VLAN
- **vlan_group** (optional): NetBox VLAN Group name this VLAN belongs to

### Default Behavior

If a VLAN is discovered in SCVMM but no mapping is configured for its ID:

- **Name**: The VLAN ID (e.g., "100" for VLAN 100)
- **Status**: "active" (unless overridden in config)
- **Other fields**: Not set

This ensures all discovered VLANs are created in NetBox, even if they don't have explicit configurations.

### Combining with Site and Environment Mappings

You can use VLAN mappings together with site and environment mappings in one configuration:

```yaml
hostname: scvmm.example.com
username: admin
password: secret
organization_config:
  site_mappings:
    - code: boi
      name: Boise
  environment_mappings:
    - code: prd
      name: Production
  vlan_mappings:
    - vid: 100
      name: Management
    - vid: 200
      name: Production
      role: production
```

## Matching Priority

When resolving cluster names, the worker tries matches in this order:

1. **Exact Match** - Full cluster name match
2. **Prefix Match** - Substring in cluster name
3. **Regex Match** - Regular expression pattern
4. **Default** - If no match found, use `default_site` or `default_group`

**Example:**

```json
{
  "site_mappings": [
    {"code": "cluster-boise", "name": "Boise Commercial", "match_type": "exact"},
    {"code": "boi", "name": "Boise Data Center", "match_type": "prefix"},
    {"code": "^boi-.*", "name": "Boise Regional", "match_type": "regex"}
  ],
  "default_site": "Uncatalogued"
}
```

| Cluster Name | Matched By | Result |
| --- | --- | --- |
| `cluster-boise` | Exact | Boise Commercial |
| `boi-cluster-01` | Prefix (no exact match) | Boise Data Center |
| `boi-remote-site` | Regex (no exact/prefix) | Boise Regional |
| `unknown-cluster` | Default | Uncatalogued |

## Real-World Example

For a company with these conventions:

- Sites: `{boi}` = Boise, `{ptl}` = Portland, `{hq}` = Headquarters
- Environments: `{prd}` = Production, `{dev}` = Dev, `{inf}` = Infrastructure

Configuration:

```yaml
hostname: scvmm-prod.internal
username: svc_scvmm
password: ServicePassword123!
organization_config:
  site_mappings:
    - code: boi
      name: Boise
      match_type: prefix
      description: Boise data center
    - code: ptl
      name: Portland
      match_type: prefix
      description: Portland data center
    - code: hq
      name: Headquarters
      match_type: prefix
      description: Corporate HQ
  environment_mappings:
    - code: prd
      name: Production Clusters
      match_type: prefix
    - code: dev
      name: Development Clusters
      match_type: prefix
    - code: inf
      name: Infrastructure Clusters
      match_type: prefix
  default_site: Unknown Location
  default_group: Unclassified
```

This will correctly classify clusters like:

- `boi-prd-cluster-01` → Boise, Production
- `ptl-dev-app-01` → Portland, Development
- `hq-inf-services` → Headquarters, Infrastructure

## Full Orb Configuration Example

This is a complete Orb configuration file showing how to integrate the SCVMM worker with NetBox Labs Diode:

```yaml
orb:
  config_manager:
    active: local

  backends:
    worker:
    common:
      diode:
        target: grpc://netbox.internal.example.com:8080/diode
        client_id: ${DIODE_CLIENT_ID}
        client_secret: ${DIODE_CLIENT_SECRET}
        agent_name: scvmm-worker

  policies:
    worker:
      scvmm_infrastructure:
        config:
          package: scvmm
        scope:
          hostname: scvmm-infra.internal.example.com
          username: ${SCVMM_USERNAME}
          password: ${SCVMM_PASSWORD}
          organization_config:
            site_mappings:
              - code: "boi"
                name: "Boise"
                match_type: "prefix"
                description: "Primary data center - Boise, ID"
              - code: "ptl"
                name: "Portland"
                match_type: "prefix"
                description: "Secondary data center - Portland, OR"
              - code: "hq"
                name: "Corporate Headquarters"
                match_type: "prefix"
                description: "Main office IT infrastructure"
              - code: "inf"
                name: "Infrastructure"
                match_type: "prefix"
                description: "Infrastructure-focused clusters"
            environment_mappings:
              - code: "prd"
                name: "Production Clusters"
                match_type: "prefix"
              - code: "dev"
                name: "Development Clusters"
                match_type: "prefix"
              - code: "inf"
                name: "Infrastructure Clusters"
                match_type: "prefix"
            default_site: "Unknown Location"
            default_group: "Unclassified"

      scvmm_production:
        config:
          package: scvmm
        scope:
          hostname: scvmm-prod.internal.example.com
          username: ${SCVMM_USERNAME}
          password: ${SCVMM_PASSWORD}
          winrm_config:
            port: 5986
            protocol: "https"
            path: "/wsman"
            transport: "kerberos"
            server_certificate_validation: "validate"
          organization_config:
            site_mappings:
              - code: "us-east-boi"
                name: "US East - Boise"
                match_type: "exact"
              - code: "us-west-ptl"
                name: "US West - Portland"
                match_type: "exact"
              - code: "us-"
                name: "United States"
                match_type: "prefix"
            environment_mappings:
              - code: "prod-"
                name: "Production"
                match_type: "prefix"
              - code: "nonprod-"
                name: "Non-Production"
                match_type: "prefix"
            default_site: "Unknown"
            default_group: "Other"
```

**Environment Variables Required:**

- `${DIODE_CLIENT_ID}`: NetBox Labs Diode client ID for authentication
- `${DIODE_CLIENT_SECRET}`: NetBox Labs Diode client secret for authentication
- `${SCVMM_USERNAME}`: Service account username for SCVMM access
- `${SCVMM_PASSWORD}`: Service account password for SCVMM access

**Key Observations:**

- Multiple policies can be configured for different SCVMM servers (e.g., infrastructure vs. production)
- Each policy has its own scope with SCVMM credentials and organization configuration
- Optional `winrm_config` section can customize connection parameters (shown in second policy)
- All sensitive values use environment variables (${...}) for security

## Troubleshooting

### Cluster not being classified correctly?

Check the logs for debug output showing which mapping rule matched. The resolver logs each resolution attempt.

### Invalid regex pattern?

The resolver will log an error and skip the invalid pattern. Verify regex syntax before using.

### Still uses defaults?

If no `organization_config` is provided, some basic defaults will be used. Add organization_config to your scope to use custom mappings.
