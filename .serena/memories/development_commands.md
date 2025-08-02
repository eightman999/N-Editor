# Development Commands and Workflow

## Installation and Setup
```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell

# Run the application
python main.py
```

## Development Workflow
- **No traditional build/test/lint commands found** - this is a desktop application
- **Entry Point**: `python main.py` starts the application
- **Dependency Management**: Use `poetry add <package>` for new dependencies
- **Environment**: Poetry handles virtual environment automatically

## Application Structure
- **Main Entry**: `main.py` with platform-specific Qt setup
- **Configuration**: Uses YAML files and JSON for settings
- **Data Storage**: Local file-based storage for designs, equipment, hulls
- **Caching**: Extensive caching system for performance optimization

## Testing Approach
- Manual testing through GUI (no automated test framework detected)
- `test_country_filter.py`: Basic functional test example
- Debug utilities in `utils/cache_debug.py` for performance testing
- Built-in debug menu with cache and conflict resolution testing

## Development Guidelines
- Follow existing CLAUDE.md performance optimization rules
- Use caching systems for heavy operations
- Implement proper error handling with zero-division checks
- Follow Qt/PyQt5 patterns and Windows 95-style UI conventions