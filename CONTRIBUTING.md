# Contributing to RTGS Lab Tools

Thank you for your interest in contributing to RTGS Lab Tools! This document provides guidelines and information for contributors.

## Getting Started

### Development Environment Setup

1. **Clone**
   ```bash
   # Fork the repository on GitHub
   git clone https://github.com/RTGS-Lab/rtgs-lab-tools.git
   cd rtgs-lab-tools
   ```

2. **Install Development Environment**
   ```bash
   # Use the automated installation script
   bash install.sh
   ```

3. **Verify Installation**
   ```bash
   # Run tests to ensure everything is working
   pytest
   
   # Check that the CLI works
   rtgs --help
   ```

## Branch Structure and Workflow

### Branch Naming Conventions

Use descriptive branch names that follow these patterns:

- **Feature branches**: `feature/short-description`
  - Example: `feature/add-error-visualization`
  - Example: `feature/improve-era5-download`

- **Bug fixes**: `fix/issue-description`
  - Example: `fix/database-connection-timeout`
  - Example: `fix/csv-parsing-error`

- **Documentation**: `docs/description`
  - Example: `docs/update-installation-guide`
  - Example: `docs/add-api-examples`

- **Refactoring**: `refactor/component-name`
  - Example: `refactor/sensing-data-extractor`
  - Example: `refactor/cli-argument-parsing`

### Git Workflow

1. **Create a Branch**
   ```bash
   git checkout master
   git pull origin master
   git switch -c feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add or update tests as needed
   - Update documentation if necessary

3. **Commit Messages**
   Use clear, descriptive commit messages:
   ```bash
   # Good examples:
   git commit -m "Add support for Parquet export in data extractor"
   git commit -m "Fix timeout handling in ERA5 download"
   git commit -m "Update CLI help text for visualization commands"
   
   # Avoid:
   git commit -m "Fix stuff"
   git commit -m "Update"
   ```

4. **Keep Branch Updated**
   ```bash
   git checkout master
   git pull origin master
   git checkout feature/your-feature-name
   git rebase master
   ```

## Code Style and Quality

### Code Formatting

We use several tools to maintain code quality:

```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Run all quality checks
black src/ tests/ && isort src/ tests/
```

### Code Style Guidelines

- **Python Style**: Follow PEP 8 and use type hints
- **Docstrings**: Use Google-style docstrings for all public functions
- **Variable Names**: Use descriptive names (`node_id` not `n`)
- **Function Length**: Keep functions focused and under 50 lines when possible
- **Error Handling**: Use specific exception types and meaningful error messages

### Testing

- **Write Tests**: All new features should include tests
- **Test Coverage**: Aim for high test coverage on new code
- **Test Types**:
  - Unit tests for individual functions
  - Integration tests for database operations
  - CLI tests for command-line interface

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/rtgs_lab_tools

# Run specific test file
pytest tests/sensing_data/test_data_extractor.py
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines (black, isort, mypy pass)
- [ ] All tests pass locally
- [ ] New features include tests
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear and descriptive

### PR Title Format

Use clear, descriptive titles:

```
Add support for multi-node error analysis visualization
Fix database connection pooling in data extractor
Update installation documentation for Windows users
Refactor CLI argument parsing for better maintainability
```

### PR Description Template

Use this template for your pull request description:

```markdown
## Summary
Brief description of what this PR does and why.

## Changes Made
- Bullet point list of specific changes
- Include any breaking changes
- Mention new dependencies if any

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] CLI commands tested

## Documentation
- [ ] README updated if needed
- [ ] Docstrings added/updated
- [ ] Examples provided if applicable

## Related Issues
Closes #123 (if applicable)
Related to #456 (if applicable)

## Screenshots/Examples
Include any relevant screenshots or example output if applicable.
```

### Review Process

1. **Automated Checks**: GitHub Actions will run tests and quality checks
2. **Code Review**: Maintainers will review your code
3. **Address Feedback**: Make requested changes
4. **Approval**: Once approved, your PR will be merged

## Development Guidelines

### Adding New Features

1. **Check Existing Issues**: Look for related issues or discussions
2. **Design Discussion**: For large features, open an issue to discuss the design
3. **Start Small**: Break large features into smaller, reviewable pieces
4. **Documentation**: Update relevant documentation

### Module Structure

When adding new functionality, follow the existing module structure:

```
src/rtgs_lab_tools/
├── new_module/
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── core_functionality.py  # Main logic
│   └── processors.py       # Data processing (if needed)
└── tests/
    └── new_module/
        ├── test_cli.py
        └── test_core_functionality.py
```

### Database Changes

If your changes affect database operations:

- Test with actual database connections
- Consider connection pooling and timeouts
- Handle network errors gracefully
- Update database documentation

### CLI Changes

For command-line interface changes:

- Follow existing argument patterns
- Add helpful help text
- Include examples in docstrings
- Test with various input combinations

## Release Process

### Version Numbering

We follow semantic versioning (SemVer):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

For maintainers releasing new versions:

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Version number bumped in `pyproject.toml`
- [ ] CHANGELOG updated
- [ ] Git tag created
- [ ] PyPI package published

## Getting Help

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: Contact Bryan Runck (runck014@umn.edu) for database access

### Common Development Tasks

```bash
# Add a new CLI command
# 1. Add command to appropriate cli.py file
# 2. Add tests
# 3. Update documentation

# Add a new data processor
# 1. Create in appropriate module
# 2. Add to __init__.py exports
# 3. Add tests and documentation

# Update dependencies
# 1. Update pyproject.toml
# 2. Test with new versions
# 3. Update requirements if needed
```

## Troubleshooting Development Issues

### Common Issues

1. **Import Errors**: Ensure you're in the virtual environment and package is installed in editable mode
2. **Test Failures**: Check if you have required credentials in `.env` file
3. **Database Connection**: Ensure UMN VPN is connected for database tests
4. **Type Errors**: Run `mypy src/` to check for type issues

### Getting Unstuck

If you're stuck:

1. Check existing issues and discussions
2. Look at similar code in the codebase
3. Run tests to see what's expected
4. Open a draft PR to get early feedback

## Recognition

Contributors will be recognized in:

- Git commit history
- Release notes for significant contributions
- README acknowledgments for major features

Thank you for contributing to RTGS Lab Tools!