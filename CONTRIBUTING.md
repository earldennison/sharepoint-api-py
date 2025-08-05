# Contributing to SharePoint API Python Library

Thank you for your interest in contributing to the SharePoint API Python library! We welcome contributions from the community.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/sharepoint-api-py.git
   cd sharepoint-api-py
   ```
3. **Install dependencies** with Poetry:
   ```bash
   poetry install --with=dev
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

### Prerequisites
- Python 3.10 or higher
- Poetry for dependency management
- Git

### Installation
```bash
# Install all dependencies including dev tools
poetry install --with=dev

# Activate the virtual environment
poetry shell

# Run tests to verify setup
poetry run pytest
```

## 📝 Making Changes

### Code Style
We use modern Python tooling for code quality:

```bash
# Format code with black
poetry run black sharepoint_api/ tests/

# Sort imports with isort  
poetry run isort sharepoint_api/ tests/

# Type checking with mypy
poetry run mypy sharepoint_api/

# Run all checks
poetry run pytest && poetry run black --check sharepoint_api/ tests/
```

### API Design Principles
- **Simple URL-based API**: Users should only need to provide SharePoint URLs
- **Automatic parsing**: No manual site/drive/folder ID extraction
- **Async/sync parity**: Both clients should have identical APIs
- **Streaming by default**: Large files should stream automatically
- **Rich data models**: Comprehensive Pydantic models for all SharePoint objects

## 🧪 Testing

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=sharepoint_api

# Run specific test file
poetry run pytest tests/test_client.py

# Run async tests specifically
poetry run pytest tests/ -k "async"
```

### Writing Tests
- Use pytest for all tests
- Include both sync and async test versions
- Mock SharePoint API responses with `requests-mock`
- Test edge cases and error conditions
- Maintain high test coverage

### Test Structure
```
tests/
├── conftest.py           # Shared fixtures
├── core/
│   └── test_client.py    # Core client tests
├── test_api.py           # Legacy API tests
├── test_config.py        # Configuration tests
└── test_integration.py   # Integration tests
```

## 📚 Documentation

### Code Documentation
- Use clear docstrings for all public methods
- Include type hints for all function parameters and returns
- Document complex business logic with inline comments

### README Updates
- Update examples if you change the API
- Keep the "Quick Start" section simple and working
- Add new features to the appropriate sections

## 🔄 Submission Process

### Pull Request Guidelines
1. **Create an issue first** for significant changes
2. **Write clear commit messages** describing the change
3. **Include tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all checks pass** (tests, linting, type checking)

### PR Template
When submitting a PR, please include:

```markdown
## Summary
Brief description of changes

## Changes Made
- List specific changes
- Include any breaking changes

## Testing
- [ ] Added/updated tests
- [ ] All tests pass
- [ ] Manual testing completed

## Documentation
- [ ] Updated docstrings
- [ ] Updated README if needed
- [ ] Added examples if appropriate
```

## 🏗️ Architecture Overview

### Project Structure
```
sharepoint_api/
├── __init__.py           # Public API exports
├── config.py             # Configuration management
├── logging.py            # Logging setup
└── core/
    ├── client.py         # Sync SharePoint client
    ├── async_client.py   # Async SharePoint client  
    ├── data_models.py    # Pydantic models
    └── errors.py         # Custom exceptions
```

### Key Components
- **SharePointClient**: Sync httpx-based client with automatic connection management
- **AsyncSharePointClient**: Async version with identical API surface
- **SharePointUrl**: URL parsing and validation
- **Data Models**: Rich Pydantic models for SharePoint objects (sites, drives, files, folders)

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version and operating system
- Poetry version and dependency versions
- Minimal code example that reproduces the issue
- Full error traceback
- Expected vs actual behavior

## 💡 Feature Requests

For new features:
- Open an issue first to discuss the feature
- Explain the use case and why it's needed
- Consider if it fits the library's design principles
- Be willing to implement it yourself or help with implementation

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers get started
- Focus on the code, not the person

## 📞 Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions
- **Documentation**: Check the README and code comments

## 🏷️ Release Process

Releases follow semantic versioning (SemVer):
- **Patch** (0.1.1): Bug fixes
- **Minor** (0.2.0): New features, backward compatible
- **Major** (1.0.0): Breaking changes

## 📄 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing to make SharePoint integration easier for Python developers! 🎉