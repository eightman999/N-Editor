# Code Style and Conventions

## Language and Style
- **Python 3.12+** with type hints where appropriate
- **Class naming**: PascalCase (`AppController`, `EquipmentModel`)
- **Method/Variable naming**: snake_case (`load_equipment`, `current_mod`)
- **Constants**: UPPER_CASE (`VERSION_FILE`, `BASE_ARMOR_VALUE_COEF`)

## PyQt5 Patterns
- **Signal/Slot architecture**: Extensive use of Qt signals for communication
- **MVC separation**: Clear separation between UI, logic, and data
- **Threading**: QThreadPool for background operations
- **Styling**: Custom Windows 95-style CSS styling

## File and Import Conventions
- **Raw strings**: Use `r""` for regex and path strings to avoid SyntaxWarning
- **Relative imports**: Use absolute imports from project root
- **Platform handling**: Conditional code for Windows/macOS/Linux

## Performance Optimizations
- **Caching**: Aggressive caching with timestamp-based invalidation
- **Lazy loading**: Background loading of heavy operations
- **Zero-division protection**: Always check divisors before division
- **Event deduplication**: Prevent duplicate event processing

## Error Handling
- **Logging**: Comprehensive logging with rotating file handlers
- **Graceful degradation**: Application continues with reduced functionality on errors
- **User feedback**: Clear error messages and progress indicators

## Data Management
- **JSON/YAML**: Primary configuration and data storage formats
- **File validation**: Extensive validation for imported game files
- **Backup systems**: Automatic backups for critical data