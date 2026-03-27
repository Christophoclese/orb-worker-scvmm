# ORB Worker SCVMM - Project Guidelines

## Code Style & Conventions

### Style Guide

- Follow PEP 8 for Python code style (indentation, line length, imports)
- Use descriptive variable/function/class names; avoid abbreviations

**Naming Conventions**:
- Modules: `lowercase_with_underscores` (e.g., `collect.py`)
- Classes: `PascalCase` (e.g., `ScvmmBackend`, `MappingResolver`)
- Constants: `UPPER_CASE` (e.g., `VM_STATUS_MAPPING`)
- Private methods/attributes: `_leading_underscore`

### Documentation

- Docstrings for all public classes/methods (use triple quotes, describe parameters and return values)
- Inline comments for complex logic, especially in mapping and transformation code
- Update `CONFIG_GUIDE.md` with any configuration changes or new options
- Update `DEVELOPMENT.md` with new testing patterns or fixture strategies when adding features

### Structure & Organization

**Key Files That Exemplify Patterns**:
- [scvmm/models.py](scvmm/models.py) — Pydantic validation models with field validators and Enum usage
- [scvmm/mapping.py](scvmm/mapping.py) — Hierarchical matching strategy (exact → prefix → regex)
- [scvmm/main.py](scvmm/main.py) — Dependency injection for testability, entity transformation pipeline
- [tests/conftest.py](tests/conftest.py) — Fixture organization and realistic mock SCVMM data

**Separation of Concerns**:
- `collect.py`: WinRM/PowerShell data collection → JSON dict
- `mapping.py`: Hierarchical name resolution (sites/environments)
- `models.py`: Pydantic validation and data structures
- `main.py`: Orchestration and entity creation
- `constants.py`: Mappings and constants (e.g., `VM_STATUS_MAPPING`: 32 SCVMM states → 6 NetBox states)

## Build & Test

**Environment Setup**:
```bash
# Install dependencies (uses uv)
uv sync --dev

# Run all tests
pytest

# Run with coverage (target 80%+)
pytest --cov=scvmm --cov-report=html --cov-report=term-missing

# Run by marker: @pytest.mark.unit, @pytest.mark.integration, @pytest.mark.e2e, @pytest.mark.slow
pytest -m unit -v
```

**Dependency Manager**: `uv` (not pip) — project uses `uv sync` for reproducible installs

**Required Dependencies**: Python 3.13+, `netboxlabs-orb-worker>=1.10.0`, `pywinrm>=0.5.0`

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed testing patterns (AAA principle) and [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for configuration examples.

## CI/CD

**GitHub Actions Workflows**:

- **Tests** ([.github/workflows/tests.yml](.github/workflows/tests.yml))  
  Runs on every push to `stable`/`develop` and all pull requests.
  - Installs dependencies via `uv sync --dev`
  - Runs tests: `pytest --cov=scvmm --cov-fail-under=80`
  - Enforces 80% code coverage (fails if below threshold)
  - Uploads coverage reports to Codecov

- **Release to PyPI** ([.github/workflows/release.yml](.github/workflows/release.yml))  
  Publishes package to PyPI on version tags.
  - Triggered on push of tags matching `v*` (e.g., `v0.1.0`)
  - Builds distribution with `python -m build`
  - Publishes using PyPA's trusted publisher (no credentials required in repo)
  - Automatically creates GitHub Release with prerelease flag for alpha/beta/rc versions

**Local Testing Before Commit**:
```bash
# Run full test suite with coverage check
pytest --cov=scvmm --cov-fail-under=80

# Or run specific test marker only
pytest -m unit -v
```

**Publishing a Release**:
```bash
# Create and push a version tag
git tag v0.2.0
git push origin v0.2.0
```
This automatically triggers the release workflow, builds the package, and publishes to PyPI.

## Architecture

**Pipeline**: Collect (WinRM) → Transform (models/mapping) → Output (Orb entities) → Diode ingestion

**Core Components**:
- **Collect**: Executes PowerShell scripts via WinRM to fetch SCVMM clusters, VMs, interfaces, disks
- **Transform**: `MappingResolver` resolves cluster names to sites/environments using hierarchical matching (exact, prefix, regex)
- **Main**: `ScvmmBackend` orchestrates workflow; creates Orb entities (Cluster, Device, VirtualMachine, VMInterface, VirtualDisk, IPAddress, VLAN)
- **Models**: Pydantic validation for `SiteMapping`, `EnvironmentMapping`, `VLANMapping`, `WinRMConfig`, `OrganizationConfig`

**Design Patterns**:
- **Dependency Injection**: Backend accepts optional entity class kwargs for testing; defaults to production Orb classes
- **Hierarchical Matching**: Three-tier fallback (exact match → case-insensitive prefix match → regex pattern match)
- **Graceful Degradation**: Missing VLAN config uses VID as name; missing cluster uses HostName; only assigns primary IPs if exactly 1 interface + 1 IPv4

## Critical Gotchas & Agent Safety

⚠️ **Security - Never log passwords**: Always log `scope` fields separately; never print full scope object containing credentials.

⚠️ **Data Integrity Issues**:
- **VM Status**: All 32 SCVMM states must be in `VM_STATUS_MAPPING` or KeyError occurs—see [scvmm/constants.py](scvmm/constants.py) for documentation
- **VLAN Resolution**: If VID not in config, defaults to name=str(VID). Always check `vlan_config_dict.get(vid)` gracefully
- **Cluster Name Matching**: Follows exact → prefix → regex order; wrong query order breaks site/environment resolution. Test with `MappingResolver` directly
- **Device Lookup**: If ClusterName is empty/None, falls back to HostName; must handle downstream in NetBox

⚠️ **Configuration Issues**:
- **WinRM Security**: Default is HTTP; production must use HTTPS with `protocol="https"`, `port=5986`
- **Field Length Limits**: NetBox validates descriptions (200 char limit) and disk names (64 char limit)—code already truncates
- **Primary IP Assignment**: Only assigns if exactly 1 interface AND 1 IPv4 address; multiple IPs are added but none marked primary

## Testing

**Markers** (pytest.ini):
- `unit` — Isolated components, mocked dependencies
- `integration` — Multi-component interactions, realistic mock data
- `e2e` — Full workflow with policy execution
- `slow` — Long-running tests

**Test Coverage Target**: 80%+

**Fixture Strategy**: See [tests/conftest.py](tests/conftest.py) for shared fixtures and realistic SCVMM mock structures. Use AAA pattern (Arrange-Act-Assert) per [DEVELOPMENT.md](DEVELOPMENT.md).

**Key Test Files**:
- [tests/test_backend_integration.py](tests/test_backend_integration.py) — Multi-component flow tests
- [tests/test_entity_creation.py](tests/test_entity_creation.py) — Entity transformation validation
- [tests/test_mapping.py](tests/test_mapping.py) — Hierarchical resolver tests

## When Adding Features

1. **New entity type?** Add to `models.py` (Pydantic model), `main.py` (creation logic), and `test_entity_creation.py` (tests)
2. **New status/state?** Update `VM_STATUS_MAPPING` in `constants.py` and add test coverage
3. **New resolver logic?** Implement in `mapping.py`, test with `MappingResolver` directly (see `test_mapping.py`)
4. **Configuration changes?** Update models in `models.py`, update `CONFIG_GUIDE.md` and examples
5. **WinRM changes?** Test integration with realistic SCVMM data (see conftest fixtures); consider Windows-specific line endings, encoding
