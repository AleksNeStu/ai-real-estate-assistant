# Contributing to AI Real Estate Assistant

Thank you for your interest in contributing to the AI Real Estate Assistant! This document provides guidelines and standards for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)
- [UI/UX Guidelines](#uiux-guidelines)

## 🤝 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, conda, etc.)
- API keys for at least one LLM provider

### Initial Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-real-estate-assistant.git
   cd ai-real-estate-assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run tests**
   ```bash
   pytest
   ```

## 💻 Development Setup

### Project Structure

```
ai-real-estate-assistant/
├── agents/              # AI agents and query processing
├── analytics/           # Analytics and tracking
├── assets/              # CSS, JS, and static files
│   ├── css/            # Stylesheets (dark mode, Tailwind)
│   └── js/             # JavaScript files (theme toggle)
├── config/              # Configuration management
├── data/                # Data loading and schemas
├── docs/                # Documentation files
├── i18n/                # Internationalization
├── models/              # AI model providers
├── notifications/       # Email and alert system
├── tests/               # Test files
├── ui/                  # UI components
├── utils/               # Utility functions
├── vector_store/        # Vector database integration
└── app_modern.py        # Main application
```

### Environment Configuration

Create a `.env` file with the following variables:

```bash
# OpenAI
OPENAI_API_KEY=your_key_here

# Anthropic
ANTHROPIC_API_KEY=your_key_here

# Google
GOOGLE_API_KEY=your_key_here

# Grok
GROK_API_KEY=your_key_here

# DeepSeek
DEEPSEEK_API_KEY=your_key_here

# Application settings
CHROMA_PERSIST_DIR=./chroma_db
```

## 📝 Code Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

#### Naming Conventions

- **Classes**: PascalCase (`PropertyAgent`, `MarketInsights`)
- **Functions/Methods**: snake_case (`create_agent`, `analyze_query`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RESULTS`, `DEFAULT_MODEL`)
- **Private methods**: Leading underscore (`_internal_method`)

#### Type Hints

Always use type hints for function signatures:

```python
from typing import List, Optional, Dict

def process_properties(
    properties: List[Property],
    filters: Optional[Dict[str, any]] = None
) -> PropertyCollection:
    """Process and filter properties."""
    pass
```

#### Docstrings

Use Google-style docstrings:

```python
def create_agent(model: str, temperature: float = 0.7) -> Agent:
    """
    Create an AI agent with specified configuration.

    Args:
        model: The model identifier (e.g., 'gpt-4o')
        temperature: Sampling temperature between 0 and 1

    Returns:
        Configured Agent instance

    Raises:
        ValueError: If model is not supported
        APIError: If API key is invalid

    Examples:
        >>> agent = create_agent('gpt-4o', temperature=0.5)
        >>> response = agent.query("Find properties")
    """
    pass
```

#### Import Organization

Group imports in this order:

```python
# Standard library
import os
from datetime import datetime
from typing import List, Optional

# Third-party packages
import streamlit as st
import pandas as pd
from langchain.agents import Agent

# Local imports
from config import settings
from models import ModelFactory
from utils import load_data
```

### Code Quality Tools

#### Linting

```bash
# Run flake8
flake8 . --max-line-length=120 --exclude=venv,__pycache__

# Run pylint
pylint app_modern.py agents/ models/
```

#### Formatting

```bash
# Format with black
black . --line-length=120

# Sort imports
isort .
```

#### Type Checking

```bash
# Run mypy
mypy . --ignore-missing-imports
```

### Error Handling

Always use specific exceptions:

```python
# Good
try:
    agent = create_agent(model)
except ValueError as e:
    logger.error(f"Invalid model: {e}")
    raise
except APIError as e:
    logger.error(f"API error: {e}")
    return None

# Bad
try:
    agent = create_agent(model)
except Exception as e:
    pass
```

## 🧪 Testing Guidelines

### Test Structure

- Place tests in `tests/` directory
- Use `test_` prefix for test files
- Mirror the source code structure

```
tests/
├── unit/
│   ├── test_agents.py
│   ├── test_models.py
│   └── test_utils.py
└── integration/
    ├── test_workflow.py
    └── test_api.py
```

### Writing Tests

```python
import pytest
from models import ModelFactory

class TestModelFactory:
    """Test suite for ModelFactory."""

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = ModelFactory.create_provider('openai', api_key='test')
        assert provider is not None
        assert provider.provider_name == 'openai'

    def test_invalid_provider_raises_error(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            ModelFactory.create_provider('invalid_provider')

    @pytest.mark.integration
    def test_model_inference(self):
        """Integration test for model inference."""
        # This test requires API key
        pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run tests matching pattern
pytest -k "test_agent"

# Skip integration tests
pytest -m "not integration"
```

### Test Coverage

Maintain at least 80% code coverage for new features:

```bash
pytest --cov=. --cov-report=term-missing
```

## 🔄 Pull Request Process

### Before Submitting

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation

3. **Run tests and linters**
   ```bash
   pytest
   flake8 .
   black . --check
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add new feature description"
   ```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: Add dark mode support with system preference detection
fix: Correct contrast ratio for form labels in dark mode
docs: Update README with new UI features
refactor: Extract theme logic into separate module
test: Add unit tests for theme toggle functionality
```

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
```

## 📚 Documentation

### Documentation Standards

- Keep README.md at repository root
- Place detailed docs in `docs/` directory
- Use Markdown for all documentation
- Include code examples
- Add screenshots for UI features

### Writing Documentation

```markdown
# Feature Name

## Overview
Brief description of the feature

## Usage
How to use the feature with examples

## Configuration
Configuration options and defaults

## Examples
Code examples demonstrating usage

## Troubleshooting
Common issues and solutions
```

## 🎨 UI/UX Guidelines

### Dark Mode Implementation

- Ensure minimum 4.5:1 contrast ratio (WCAG AA)
- Support system preference detection
- Provide manual override option
- Test on multiple devices

### CSS Standards

- Use CSS custom properties for theming
- Follow BEM naming convention for custom classes
- Use Tailwind utility classes where possible
- Ensure responsive design (mobile-first)

### Accessibility

- Use semantic HTML
- Provide ARIA labels
- Ensure keyboard navigation
- Test with screen readers
- Support reduced motion preferences

### Form Elements

```python
# Good: Clear label with help text
st.text_input(
    label="Email Address",
    help="We'll never share your email",
    placeholder="user@example.com"
)

# Add proper validation
if email and not is_valid_email(email):
    st.error("Please enter a valid email address")
```

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's reproducible
3. Test with latest version

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen

**Screenshots**
If applicable, add screenshots

**Environment**
- OS: [e.g., Windows 10]
- Python version: [e.g., 3.10.5]
- Browser: [e.g., Chrome 120]

**Additional context**
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired feature

**Describe alternatives you've considered**
Alternative solutions or features

**Additional context**
Mockups, examples, or references
```

## 📞 Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers for sensitive issues

## 🏆 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to AI Real Estate Assistant!** 🎉

Your contributions help make this project better for everyone.
