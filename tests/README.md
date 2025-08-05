# SharePoint API Tests

This directory contains tests for the SharePoint API wrapper. The tests are organized into three main categories:

1. **API Tests** (`test_api.py`): Tests for the SharePointClient class and its methods
2. **Data Model Tests** (`test_data_models.py`): Tests for the Pydantic models that represent SharePoint resources
3. **Integration Tests** (`test_integration.py`): End-to-end tests that simulate complete workflows

## Running Tests

To run the tests, you need to have pytest installed. You can install it along with other test dependencies with:

```bash
pip install pytest pytest-cov requests-mock
```

### Running all tests

```bash
pytest
```

### Running with verbose output

```bash
pytest -vs
```

### Running tests with coverage report

```bash
pytest --cov=sharepoint_api
```

For a more detailed coverage report:

```bash
pytest --cov=sharepoint_api --cov-report=html
```

This will generate an HTML report in the `htmlcov` directory.

## Test Structure

### Fixtures

Common test fixtures are defined in `conftest.py`, including:

- `setup_test_env`: Sets up environment variables for testing
- `test_config`: Provides a test SharepointConfig instance
- `mock_env_config`: Provides a SharepointConfig loaded from environment variables

### Mock Responses

The tests use the `unittest.mock` module to mock API responses and avoid making real API calls. The `MockResponse` class is used to simulate HTTP responses.

### Test Categories

#### API Tests

Tests for the `SharePointClient` class, including:
- Authentication and token management
- Site and drive operations
- Error handling

#### Data Model Tests

Tests for the Pydantic models, including:
- RawFile operations
- SharepointFile operations
- SharepointFolder operations
- SharepointSite operations
- SharepointSiteDrive operations

#### Integration Tests

Tests for complete workflows that combine multiple operations, including:
- Searching for a site and navigating its structure
- Downloading files from SharePoint

## Adding New Tests

When adding new tests:

1. Follow the existing test pattern for mocking API responses
2. Use fixtures from `conftest.py` when possible
3. Ensure that tests don't make real API calls to SharePoint
4. Consider adding tests for both success and error cases

## Running Only Specific Tests

To run a specific test file:

```bash
pytest tests/test_api.py
```

To run a specific test class:

```bash
pytest tests/test_api.py::TestSharePointClient
```

To run a specific test method:

```bash
pytest tests/test_api.py::TestSharePointClient::test_initialization
``` 