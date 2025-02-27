# Contributing to DocBrain

Thank you for considering contributing to DocBrain! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in the Issues section
- Use the bug report template when creating a new issue
- Include detailed steps to reproduce the bug
- Include any relevant logs or error messages

### Suggesting Features

- Check if the feature has already been suggested in the Issues section
- Use the feature request template when creating a new issue
- Clearly describe the feature and its potential benefits
- Consider how the feature fits into the project's scope

### Pull Requests

1. Fork the repository
2. Create a new branch for your changes (`git checkout -b feature/amazing-feature`)
3. Make your changes and commit them with clear, descriptive messages
4. Push your branch to your fork (`git push origin feature/amazing-feature`)
5. Open a pull request against the `main` branch

## Development Setup

1. Clone your fork and set up the development environment:

```bash
git clone https://github.com/yourusername/DocBrain.git
cd DocBrain
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

2. Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the tests to ensure everything is working:

```bash
pytest
```

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Python Styleguide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use meaningful variable and function names
- Document functions and classes using docstrings
- Maintain test coverage for new code

### Documentation Styleguide

- Use Markdown for documentation
- Keep API documentation up-to-date when changing endpoints
- Document new features thoroughly

## Additional Notes

### Issue and Pull Request Labels

| Label | Description |
| --- | --- |
| `bug` | Indicates an issue with the current code |
| `enhancement` | New feature or request |
| `documentation` | Improvements or additions to documentation |
| `good first issue` | Good for newcomers |

## Attribution

This Contributing guide is adapted from the open-source contribution guidelines templates. 