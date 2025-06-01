# Contributing to Claude Container

Thank you for your interest in contributing to Claude Container! This guide will help you get started.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Architecture](#architecture)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/claude-container.git
   cd claude-container
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/original/claude-container.git
   ```

## Development Setup

1. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

4. Run the test suite to verify setup:
   ```bash
   poetry run pytest
   ```

## Architecture

Before contributing, please familiarize yourself with the project architecture:

- 📖 **[Architecture Overview](docs/architecture_overview.md)** - Comprehensive system design documentation
- 📊 **[Architecture Diagrams](docs/architecture_overview.md#architecture-diagram)** - Visual representation of components
- 📝 **[Architecture Decision Records](docs/adr/)** - Important design decisions and their rationale

Key architectural components:
- **CLI Layer**: User interface and command handling
- **Service Layer**: Business logic and orchestration
- **Core Layer**: Low-level Docker and container operations
- **Models**: Data structures and validation
- **Utils**: Cross-cutting concerns

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=claude_container

# Run specific test file
poetry run pytest tests/test_specific.py

# Run with verbose output
poetry run pytest -v
```

### Code Quality Checks

Before submitting a PR, ensure your code passes all quality checks:

```bash
# Lint checks
poetry run ruff check claude_container/

# Type checks
poetry run mypy claude_container/

# Check file length limits (max 400 lines)
python scripts/check_file_length.py
```

### Writing Tests

- Place tests in the `tests/` directory, mirroring the source structure
- Use pytest fixtures for common test setup
- Mock external dependencies (Docker API, filesystem, etc.)
- Aim for high test coverage, especially for new features

## Code Style

### General Guidelines

- Follow PEP 8 Python style guidelines
- Use type hints for all function parameters and return values
- Keep functions focused and single-purpose
- Maximum file length: 400 lines (enforced by linting)
- Use descriptive variable and function names

### File Organization

- Keep related functionality together
- Use clear module and package names
- Follow the existing directory structure

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings format
- Keep docstrings concise but informative
- Update relevant documentation when changing functionality

## Submitting Changes

### Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. Run all quality checks:
   ```bash
   poetry run ruff check claude_container/
   poetry run mypy claude_container/
   python scripts/check_file_length.py
   poetry run pytest
   ```

4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Create a Pull Request

### Commit Messages

Follow conventional commit format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or modifications
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

### Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Keep PRs focused on a single feature or fix

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Docker version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Any relevant error messages or logs

## Code of Conduct

Please be respectful and professional in all interactions. We're building this together!

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Check existing issues and PRs
- Review the architecture documentation

Thank you for contributing to Claude Container! 🚀