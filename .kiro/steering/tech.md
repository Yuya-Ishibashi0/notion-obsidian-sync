# Technology Stack

## Core Technologies
- **Python 3.x** - Main programming language
- **PyYAML** - Configuration file parsing
- **python-dotenv** - Environment variable management
- **notion-client** - Notion API integration
- **requests** - HTTP client for API calls

## Development Tools
- **pytest** - Testing framework
- **pytest-mock** - Mocking for tests
- **pytest-asyncio** - Async testing support

## Architecture Patterns
- **Service Layer Pattern** - Business logic separated into service classes
- **Data Model Pattern** - Structured data classes for configuration and entities
- **Orchestrator Pattern** - Central coordination through SyncOrchestrator
- **CLI Command Pattern** - Modular command structure with argparse

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create default configuration
python main.py config --create

# Validate configuration
python main.py config --validate
```

### Development
```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_sync_orchestrator.py

# Run with verbose output
pytest -v

# Run tests with coverage (if configured)
pytest --cov=services --cov=models --cov=utils
```

### Application Usage
```bash
# Test connection
python main.py test

# Preview sync
python main.py preview

# Full sync
python main.py sync

# Sync specific page
python main.py sync --page-id <page_id>

# Check status
python main.py status
```

## Configuration Management
- YAML-based configuration with environment variable substitution
- Separate `.env` file for sensitive data
- Comprehensive validation with detailed error messages