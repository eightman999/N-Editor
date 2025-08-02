# Architecture Patterns and Design

## Core Architecture
- **MVC Pattern**: Model-View-Controller with clear separation
- **Observer Pattern**: Extensive use of Qt signals/slots for communication
- **Strategy Pattern**: Equipment calculators with registry-based selection
- **Factory Pattern**: Dynamic creation of UI components and parsers

## Key Design Patterns

### Cache Management
- **Decorator Pattern**: `@performance_measure` for timing
- **Manager Pattern**: Centralized cache management with metadata
- **Timestamp-based Invalidation**: File modification time tracking

### Data Processing
- **Parser Strategy**: PLY-based parsers for different HOI4 file formats
- **Calculator Registry**: Equipment-specific calculation strategies
- **Validation Pipeline**: Multi-stage file validation and parsing

### UI Architecture
- **Composite Pattern**: Complex UI built from reusable components
- **Command Pattern**: Background task execution with progress tracking
- **State Management**: Centralized application state in AppController

## Threading Model
- **QThreadPool**: Background operations for file I/O and parsing
- **Worker Pattern**: Separate worker classes for different task types
- **Signal-based Communication**: Thread-safe UI updates via Qt signals

## Performance Design
- **Lazy Loading**: Deferred loading of expensive resources
- **Sprite Sheets**: Image optimization for flags and icons
- **Database Abstraction**: File-based storage with caching layer

## Data Flow
1. **User Input** → View Components
2. **UI Events** → AppController (Central Hub)
3. **Business Logic** → Model Classes
4. **Data Persistence** → File System with Caching
5. **Background Tasks** → QThreadPool Workers
6. **Results** → Signal-based UI Updates