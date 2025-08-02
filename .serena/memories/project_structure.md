# Project Structure (MVC Architecture)

## Directory Organization

### Core Application
- `main.py`: Application entry point with platform-specific setup
- `CLAUDE.md`: Existing development guidelines and rules

### MVC Components
- **Models** (`models/`):
  - `app_settings.py`: Application configuration management
  - `data_models.py`: Core data structures (Equipment, Hull, Ship, Fleet)
  - `equipment_model.py`: Equipment data management
  - `hull_model.py`: Hull data management

- **Views** (`views/`):
  - `main_window.py`: Primary application window
  - `*_view.py`: Specialized UI components (equipment, design, fleet, etc.)
  - `*_form.py`: Data entry forms
  - `*_dialog.py`: Modal dialogs

- **Controllers** (`controllers/`):
  - `app_controller.py`: Main application logic coordinator
  - `naval_export_controller.py`: Export functionality

### Specialized Components
- **Parsers** (`parser/`): PLY-based parsers for HOI4 script formats
  - `StateParser.py`, `NavalOOBParser.py`, `CountryColorParser.py`, etc.
  - Generated parse tables (`*_parsetab.py`)

- **Utilities** (`utils/`):
  - Cache management, performance monitoring
  - Equipment calculators, stats computation
  - Map viewing, icon management
  - Synchronization and conflict resolution

- **Data Management** (`data/`, `config/`): User data and configuration
- **Assets** (`assets/`): Icons, images, and resources
- **Exporters** (`exporters/`): Output format handlers