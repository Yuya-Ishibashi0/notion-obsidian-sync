# Project Structure

## Root Level
- `main.py` - CLI entry point with comprehensive command handling
- `config.yaml` - Configuration template with environment variable substitution
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies

## Core Directories

### `/models`
Data models and configuration classes:
- `config.py` - Configuration data classes (NotionConfig, ObsidianConfig, etc.)
- `notion.py` - Notion-specific data models
- `markdown.py` - Markdown conversion result models

### `/services`
Business logic and core functionality:
- `sync_orchestrator.py` - Main coordination class for sync operations
- `notion_client.py` - Notion API client wrapper
- `data_processor.py` - Core data processing logic
- `advanced_block_converter.py` - Complex Notion block conversion
- `concurrent_processor.py` - Parallel processing utilities
- `cache_manager.py` - Caching functionality
- `link_processor.py` - Link handling and processing
- `conversion_limitations.py` - Conversion constraint management

### `/utils`
Utility functions and helpers:
- `config_loader.py` - Configuration file loading and validation
- `file_manager.py` - File system operations

### `/tests`
Comprehensive test suite:
- Test files follow `test_<module_name>.py` naming convention
- Includes unit tests, integration tests, and configuration tests
- Uses pytest with mocking capabilities

### `/scripts`
Automation and setup scripts:
- `setup_scheduler.py` - Scheduling functionality setup

## Code Organization Principles
- **Separation of Concerns** - Models, services, and utilities are clearly separated
- **Single Responsibility** - Each service class has a focused purpose
- **Dependency Injection** - Configuration passed to services rather than global access
- **Error Handling** - Comprehensive error handling with custom exception types
- **Logging** - Structured logging throughout the application

## File Naming Conventions
- Snake_case for Python files and directories
- Descriptive names that indicate functionality
- Test files prefixed with `test_`
- Service classes end with appropriate suffixes (Client, Processor, Manager, etc.)

## Import Structure
- Models imported from `models.*`
- Services imported from `services.*`
- Utils imported from `utils.*`
- Relative imports used within packages