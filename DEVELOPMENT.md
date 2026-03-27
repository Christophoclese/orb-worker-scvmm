# Development Guide for orb-worker-scvmm

This guide covers testing patterns, best practices, and code contribution guidelines.

## Setup and Project Management

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python dependency management. The project includes a virtual environment at `.venv/`.

### Installing Dependencies

To install project dependencies:

```bash
# Install all dependencies from pyproject.toml
uv sync

# Install with dev dependencies only
uv sync --dev

# Update all dependencies to latest compatible versions
uv sync --upgrade
```

### Running Commands in the Project Environment

Use `uv run` to execute Python commands within the project's virtual environment:

```bash
# Run Python scripts
uv run python script.py

# Run pytest (tests automatically inherit the environment)
uv run pytest

# Run with coverage
uv run pytest --cov=scvmm --cov-report=html
```

### Virtual Environment

The project's virtual environment is located at `.venv/`. You can also activate it directly:

```bash
# On Linux/macOS
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

Once activated, you can run commands directly without `uv run`:

```bash
pytest --cov=scvmm
python -m pytest tests/test_models.py -v
```

### Release Process

The project uses a `release.sh` script to manage version bumping and publishing. The script automates:
1. Version bumping with `uv version --bump`
2. Creating git commit and tag
3. Publishing to PyPI via GitHub Actions

#### Understanding `uv version`

The `uv version` command manages the project version stored in `pyproject.toml`. The script uses `uv version --bump` to automatically increment versions:

```bash
# `uv version --bump` accepts these arguments:
uv version --bump major      # Bump major (1.0.0 → 2.0.0)
uv version --bump minor      # Bump minor (1.0.0 → 1.1.0)
uv version --bump patch      # Bump patch (1.0.0 → 1.0.1)
uv version --bump alpha      # Bump/create alpha prerelease (1.0.0 → 1.0.1a1)
uv version --bump beta       # Bump/create beta prerelease (1.0.0 → 1.0.1b1)
uv version --bump rc         # Bump/create RC prerelease (1.0.0 → 1.0.1rc1)
uv version --bump stable     # Finalize prerelease (1.0.0rc1 → 1.0.0)
```

The `--bump` flag can be specified **multiple times** to combine operations:

```bash
# Combine version bump with prerelease creation
uv version --bump patch --bump alpha   # 1.0.0 → 1.0.1a1
uv version --bump minor --bump beta    # 1.0.0 → 1.1.0b1
uv version --bump major --bump rc      # 1.0.0 → 2.0.0rc1
```

#### Using the Release Script

The `release.sh` script wraps `uv version --bump` with git operations and validation:

```bash
# Basic version bumps
./release.sh patch              # Bump patch: 1.0.0 → 1.0.1
./release.sh minor              # Bump minor: 1.0.0 → 1.1.0
./release.sh major              # Bump major: 1.0.0 → 2.0.0

# Prerelease bumps (increment existing prerelease)
./release.sh alpha              # Bump alpha: 1.0.0a1 → 1.0.0a2
./release.sh beta               # Bump beta: 1.0.0b1 → 1.0.0b2
./release.sh rc                 # Bump RC: 1.0.0rc1 → 1.0.0rc2

# Combined: version bump + start new prerelease cycle
./release.sh patch alpha        # Bump patch + alpha: 1.0.0 → 1.0.1a1
./release.sh minor beta         # Bump minor + beta: 1.0.0 → 1.1.0b1
./release.sh major rc           # Bump major + RC: 1.0.0 → 2.0.0rc1

# Finalize a prerelease (remove alpha/beta/rc suffix)
./release.sh stable             # Finalize: 1.0.0rc1 → 1.0.0
```

#### How the Script Works

1. **Validation**: Checks that git is clean and `uv` is installed (unless `--force` is used)
2. **Preview**: Shows what version bump would occur with `--dry-run`
3. **Confirmation**: Prompts for confirmation (skipped with `--force`)
4. **Version Bump**: Calls `uv version --bump` (single or multiple times) to update `pyproject.toml` and `uv.lock`
5. **Git Operations**: Creates commit and annotated tag with the new version
6. **Publishing**: Pushes to `origin stable` branch and pushes the version tag
7. **GitHub Actions**: Detects the version tag and publishes to PyPI automatically

#### Release Examples

**Releasing a stable patch version**:
```bash
./release.sh patch          # 1.2.3 → 1.2.4
# Creates: commit "bump version to 1.2.4" and tag "v1.2.4"
```

**Starting an alpha cycle for next patch**:
```bash
./release.sh patch alpha    # 1.2.3 → 1.2.4a1
# Creates: commit "bump version to 1.2.4a1" and tag "v1.2.4a1"
```

**Releasing multiple alpha builds**:
```bash
./release.sh alpha          # 1.2.4a1 → 1.2.4a2
./release.sh alpha          # 1.2.4a2 → 1.2.4a3
```

**Finalizing an alpha release**:
```bash
./release.sh stable         # 1.2.4a3 → 1.2.4
# Creates: commit "bump version to 1.2.4" and tag "v1.2.4"
```

#### Options

```bash
./release.sh --force patch  # Skip git clean check and confirmation
./release.sh --help         # Show usage and all available commands
```

#### Prerequisites

- Git repository must be clean (no uncommitted changes) unless `--force` is used
- `uv` must be installed
- You must have push access to `origin stable` branch
- GitHub Actions CI must pass for the tag to be published to PyPI

## Project Architecture

```
scvmm/
├── __init__.py           # Package initialization
├── constants.py          # VM status mappings, PowerShell scripts
├── models.py             # Pydantic data models for validation
├── mapping.py            # MappingResolver for site/env name resolution
├── collect.py            # WinRM data collection from SCVMM
├── main.py               # ScvmmBackend implementation
└── __pycache__/

tests/
├── __init__.py
├── conftest.py           # Shared fixtures and configuration
├── test_models.py        # Model validation tests
├── test_mapping.py       # Mapping resolver tests
├── test_collect.py       # Data collection tests (WinRM mocked)
├── test_entity_creation.py  # Entity creation tests (integration)
├── test_backend_integration.py  # End-to-end backend tests
└── __pycache__/
```

### Core Components

- **`scvmm/constants.py`**: Extracted VM status mappings and PowerShell script for testability
- **`scvmm/main.py`**: `ScvmmBackend` class with dependency injection for testing
- **`scvmm/collect.py`**: `collect_scvmm_data()` function for WinRM communication
- **`scvmm/mapping.py`**: `MappingResolver` for hierarchical name matching
- **`scvmm/models.py`**: Pydantic models for config validation

## Testing Patterns

### 1. Unit Tests (test_*.py files)

**Purpose**: Test individual functions with mocked dependencies.
**Speed**: Fast (typically <50ms per test)
**Coverage**: 100% of unit functionality

**Example: Testing Status Mapping**
```python
def test_vm_status_mapping_all_types():
    """Test that all 32 VM status mappings are covered."""
    backend = ScvmmBackend()
    
    for scvmm_status, expected_status in VM_STATUS_MAPPING.items():
        result = backend.get_status_for_vm(scvmm_status, "test-vm")
        assert result == expected_status.lower()
```

**Key Principles**:
- Mock all external dependencies (WinRM, file I/O, network)
- Each test is independent and can run in any order
- Use descriptive test names that explain what is being tested
- Arrange-Act-Assert (AAA) pattern

### 2. Integration Tests (test_entity_creation.py)

**Purpose**: Test entity creation from realistic mock SCVMM data.
**Speed**: Medium (typically 50-200ms per test)
**Coverage**: Component interactions, business logic

**Example: Testing VLAN Creation from Config**
```python
def test_vlan_created_from_interface_untagged_vlan(self, mock_scvmm_data, org_config_with_mappings, mapping_resolver):
    """Test that VLAN entities are created from interface untagged VLAN."""
    backend = ScvmmBackend()
    entities = backend.create_entities_from_data(
        mock_scvmm_data, mapping_resolver, org_config_with_mappings
    )
    
    interface_entities = [
        e for e in entities
        if e.vm_interface is not None and e.vm_interface.untagged_vlan is not None
    ]
    
    assert len(interface_entities) > 0
```

**Key Principles**:
- Use realistic test data (see `conftest.py` fixtures)
- Test multiple entities together (cluster → VM → interface → VLAN)
- Verify mappings and transformations are applied correctly

### 3. End-to-End Tests (test_backend_integration.py)

**Purpose**: Test full backend workflow from policy to entities.
**Speed**: Slower (typically 200-500ms per test)
**Coverage**: Complete workflow, policy validation, error handling

**Example: Full Backend Workflow**
```python
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
    
    assert len(entities) > 0
```

**Key Principles**:
- Test happy paths and error paths
- Use `@patch` decorator for mocking external systems
- Verify correct exception types are raised for error handling

## Using Fixtures

### Mock SCVMM Data

The `mock_scvmm_data` fixture provides realistic test data:
```python
def test_cluster_creation(mock_scvmm_data, mapping_resolver):
    backend = ScvmmBackend()
    entities = backend.create_entities_from_data(mock_scvmm_data, mapping_resolver, None)
    assert len(entities) > 0
```

### Organization Configuration

The `org_config_with_mappings` fixture includes site, environment, and VLAN mappings:
```python
def test_vlan_mapping(org_config_with_mappings):
    vlan_config_dict = {
        v.vid: v.model_dump(exclude_none=True)
        for v in org_config_with_mappings.vlan_mappings
    }
    assert 100 in vlan_config_dict
    assert vlan_config_dict[100]["name"] == "Management"
```

### WinRM Mocking

Different WinRM scenarios are available:
```python
# Success case
@patch('scvmm.collect.winrm.Session')
def test_collect_success(self, mock_session_class, mock_scvmm_data):
    mock_session_class.return_value = mock_winrm_session_with_data(mock_scvmm_data)
    # test code

# Error case
@patch('scvmm.collect.winrm.Session')
def test_collect_error(self, mock_session_class):
    mock_session_class.return_value = mock_winrm_session_error()
    # test code
```

## Dependency Injection for Testing

The `ScvmmBackend` class supports dependency injection of entity classes:

```python
# In tests, inject mock entity classes
mock_vlan_class = Mock()
backend = ScvmmBackend(vlan_class=mock_vlan_class)

# Production code uses real classes (backward compatible)
backend = ScvmmBackend()
```

This allows testing entity creation logic without side effects.

## Mocking Best Practices

### 1. Mock External Systems

```python
# Good: Mock WinRM specifically
@patch('scvmm.collect.winrm.Session')
def test_collect(self, mock_session_class):
    # WinRM is mocked, our code is tested

# Bad: Mocking too much
@patch('scvmm.collect.winrm')
@patch('scvmm.collect.json')
def test_collect(self, mock_json, mock_winrm):
    # Too granular, hard to understand what's being tested
```

### 2. Return Realistic Data

```python
# Good: Mock returns realistic JSON
mock_session.run_ps.return_value = Mock(
    status_code=0,
    std_out=json.dumps(mock_scvmm_data).encode(),
    std_err=b'',
)

# Bad: Mock returns oversimplified data
mock_session.run_ps.return_value = Mock(
    status_code=0,
    std_out=b'{}',  # Empty JSON - doesn't test real behavior
)
```

### 3. Verify Mock Interactions

```python
# Good: Verify mocks were called correctly
mock_session_class.return_value.run_ps.assert_called_once()
call_args = mock_session_class.call_args
assert call_args[1]["auth"] == ("domain\\user", "password")

# Bad: Not verifying mock behavior
# Mock is set but no verification that it was actually used
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_entity_creation.py

# Run specific test
pytest tests/test_entity_creation.py::TestClusterCreation::test_cluster_created_for_each_scvmm_cluster
```

### Coverage Analysis

```bash
# Generate coverage report in terminal
pytest --cov=scvmm --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=scvmm --cov-report=html

# View HTML report
open htmlcov/index.html

# Show which lines aren't covered
pytest --cov=scvmm --cov-report=term-missing:skip-covered
```

### Filtering Tests

```bash
# Run only tests matching a pattern
pytest -k "vlan"  # All tests with "vlan" in name

# Run tests except slow ones
pytest -m "not slow"

# Run only integration tests
pytest tests/test_entity_creation.py tests/test_backend_integration.py
```

## Adding New Tests

### Step 1: Identify What to Test

- What function/method needs testing?
- What are the happy paths and error paths?
- What fixtures do you need?

### Step 2: Create Test Function

```python
def test_new_functionality(self, mock_scvmm_data, mapping_resolver):
    """Test that [specific behavior] works correctly."""
    # Arrange: Set up test data and objects
    backend = ScvmmBackend()
    
    # Act: Call the function being tested
    entities = backend.create_entities_from_data(
        mock_scvmm_data, mapping_resolver, None
    )
    
    # Assert: Verify the results
    assert len(entities) > 0
    assert all(hasattr(e, 'cluster') for e in entities)
```

### Step 3: Run and Verify

```bash
# Run just your new test
pytest tests/test_file.py::TestClass::test_new_functionality -v

# Generate coverage to see if your test adds coverage
pytest --cov=scvmm --cov-report=term-missing
```

## Common Testing Errors

### Error: "AttributeError: 'Mock' object has no attribute 'status_code'"

**Cause**: WinRM mock not properly configured.

```python
# Wrong
mock_session.run_ps.return_value = Mock()  # No properties set

# Right
mock_session.run_ps.return_value = Mock(
    status_code=0,
    std_out=b'{}',
    std_err=b'',
)
```

### Error: "TypeError: 'Mock' object is not iterable"

**Cause**: Forgetting that fixtures are parameters, not global variables.

```python
# Wrong
def test_something():
    data = mock_scvmm_data  # Not a fixture

# Right
def test_something(mock_scvmm_data):  # Fixture injected
    data = mock_scvmm_data
```

### Error: "AssertionError: assert 0 == 1"

**Cause**: Test data doesn't match expectations.

```python
# Debug by printing actual data
def test_something(mock_scvmm_data):
    print(f"Clusters: {len(mock_scvmm_data['Clusters'])}")
    print(f"VMs: {len(mock_scvmm_data['VMs'])}")
    # Shows actual counts to fix your assertion
```

## Continuous Improvement

### Coverage Goals

- **80%+**: Minimum for v1.0 release
- **90%+**: Target for production-grade code
- **100%**: Aim for critical paths (VLAN, entity creation, error handling)

### Refactoring for Testability

If code is hard to test:
1. **Extract functions**: Move complex logic into standalone functions
2. **Add parameters**: Replace hard-coded values with parameters
3. **Inject dependencies**: Use constructor/parameter injection instead of module imports
4. **Separate concerns**: Keep I/O (WinRM, files) separate from business logic

Example:
```python
# Before: Hard to test (WinRM embedded)
def create_entities():
    data = collect_scvmm_data(hostname, user, pwd)
    return process(data)

# After: Easy to test (data is parameter)
def create_entities(data, resolver):
    return process(data, resolver)

# Call with real data in production, mock data in tests
```

### Monitoring Test Health

```bash
# Run tests with pytest-watch for continuous feedback
pytest-watch -- -v

# Run tests on file save and show coverage
pytest-watch -- --cov=scvmm --cov-report=term-missing
```

## Contributing

1. Write tests first (TDD approach)
2. Make tests pass with implementation
3. Ensure coverage remains at 80%+
4. Run `pytest --cov=scvmm` before committing
5. Update this guide if adding new testing patterns
