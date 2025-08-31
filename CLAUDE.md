# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is LivChatSetup, a modular Linux server configuration system built in Python that deploys Docker Swarm applications via Portainer API with interactive menu interface. The system provides automated setup for infrastructure (Traefik, Portainer) and applications (Chatwoot, Directus, N8N, etc.).

## Common Commands

### Running the System
```bash
# Main execution (always starts with interactive menu)
sudo python3 main.py

# One-liner installation from web
bash <(curl -sSL setup.livchat.ai)

# Log control modes (local execution)
sudo python3 main.py           # Padrão - sem logs no console
sudo python3 main.py --quiet   # Apenas ERROR e CRITICAL
sudo python3 main.py --verbose # Todos os logs (DEBUG)

# Log control modes (web installation)
bash <(curl -sSL setup.livchat.ai)           # Padrão - sem logs no console
bash <(curl -sSL setup.livchat.ai) --quiet   # Apenas ERROR e CRITICAL  
bash <(curl -sSL setup.livchat.ai) --verbose # Todos os logs (DEBUG)
```

### Development Commands
```bash
# Install Python dependencies
pip install -r requirements.txt

# Check logs
tail -f /var/log/setup_inicial.log

# View service credentials
ls -la /root/dados_vps/

# Docker Swarm operations
docker service ls
docker stack ls
docker node ls
```

## Architecture Overview

### Core Structure
- **main.py**: Entry point that validates prerequisites and launches interactive menu
- **config.py**: Global configurations, logging setup, and system constants
- **requirements.txt**: Python dependencies (jinja2, requests)
- **livchat-config.json**: Persistent configuration storage for system settings

### Module System
The system uses a modular architecture with three main directories:

1. **setup/**: Individual setup modules that inherit from `BaseSetup`
   - Each module implements `validate_prerequisites()` and `run()` methods
   - Deploy via `PortainerAPI().deploy_service_complete()` method
   - Examples: `chatwoot_setup.py`, `traefik_setup.py`, `directus_setup.py`

2. **templates/docker-compose/**: Jinja2 templates for Docker Compose stacks
   - All templates use `{{ network_name }}` for external network reference
   - Include Traefik labels for automatic SSL and routing
   - Parametrized with variables like `domain`, `encryption_key`, credentials

3. **utils/**: Core utilities and coordinators
   - `interactive_menu.py`: Main menu interface with TUI selection and post-installation options
   - `module_coordinator.py`: Module mapping and execution coordinator
   - `config_manager.py`: Persistent configuration management (livchat-config.json)
   - `portainer_api.py`: Portainer API integration for stack deployment
   - `template_engine.py`: Jinja2 template processing
   - `cloudflare_api.py`: DNS automation integration with zone selection menu

### Key Classes
- **BaseSetup**: Abstract base class for all setup modules with common functionality
- **BasicSetup**: Unified setup module for system configuration (email, hostname, DNS, network, timezone)
- **ConfigManager**: Handles persistent configuration in livchat-config.json
- **PortainerAPI**: Handles Docker Swarm deployment via Portainer API
- **InteractiveMenu**: Manages the interactive CLI menu system with TUI selection
- **ModuleCoordinator**: Maps and executes setup modules, handles dependencies

## Development Patterns

### Adding New Services
To add a new service stack, create these files:
1. `setup/<service>_setup.py` - Setup module inheriting from BaseSetup
2. `templates/docker-compose/<service>.yaml.j2` - Docker Compose template
3. Update `utils/module_coordinator.py` - Import and map the new module
4. Update `utils/interactive_menu.py` - Add menu option and execution handler

### Template Standards
- Use `{{ network_name }}` for external network reference (never hardcode)
- Include standard Traefik labels for SSL and routing
- Parametrize all credentials, domains, and configuration values
- Follow naming convention: `<service>.yaml.j2`

### Deployment Flow
1. Interactive menu with TUI selection (multiple apps can be selected)
2. Basic setup execution (system update, timezone, email, hostname, DNS, network)
3. Validate prerequisites (Docker, Swarm, network, databases)
4. Collect user inputs (domain, email, passwords) with suggestion pattern
5. Generate secure keys and passwords
6. Optionally setup DNS via Cloudflare API with interactive zone selection
7. Deploy stack via `PortainerAPI.deploy_service_complete()`
8. Wait for services to be healthy
9. Save credentials to `/root/dados_vps/dados_<service>`
10. Post-installation menu (continue with more apps or exit)

### Error Handling
- All modules use structured logging via `config.setup_logging()`
- Logs written to `/var/log/setup_inicial.log` with rotation
- Colored console output for better UX
- Comprehensive error catching with user-friendly messages

## Important Notes

### Security
- System requires root privileges (`os.geteuid() != 0` check)
- Credentials stored in `/root/dados_vps/dados_*` files
- Auto-generated secure passwords and encryption keys
- All web services deployed with HTTPS via Let's Encrypt
- Persistent configuration stored securely in `/root/livchat-config.json`

### Database Sharing
- Directus reuses Chatwoot's PostgreSQL database by design
- Template uses `DB_DATABASE=chatwoot` instead of creating separate DB
- Simplifies infrastructure and reduces operational overhead

### Service Dependencies
- Basic setup (includes hostname) → Docker+Swarm → Traefik → Portainer is the required sequence
- Applications can be installed in any order after infrastructure is ready
- PostgreSQL with PgVector is shared across multiple applications

### Logging and Monitoring
- **Structured logging** with timestamps and log levels (`HH:MM:SS.mmm | LEVEL | message`)
- **File rotation** (10MB, 5 backups) at `/var/log/setup_inicial.log`
- **Console output** with color coding (configurable via CLI arguments)
- **Log levels**: 3 modes available
  - **Padrão** (default): Console silencioso, arquivo recebe tudo
  - **--quiet**: Console mostra ERROR/CRITICAL, arquivo recebe tudo  
  - **--verbose**: Console mostra DEBUG completo, arquivo recebe tudo
- **Service health monitoring** via Portainer API

### Current Status
- **Module Count**: 34 total modules (reduced from 35 after hostname integration)
- **Infrastructure modules**: Complete and production-ready (basic setup is unified)
- **Database modules**: Complete (Redis, PostgreSQL+PgVector, MinIO)
- **Applications**: Chatwoot and Directus are production-ready
- **Evolution API v2**: Available but in testing
- **Interactive Experience**: Full TUI menu with search, multi-selection, and post-install options
- **Configuration Persistence**: All settings stored in livchat-config.json
- **Other applications**: Available via menu but may need testing

## Configuration Management

### Persistent Storage
- **Primary config**: `/root/livchat-config.json` - Main configuration file with all system settings
- **Credentials backup**: `/root/dados_vps/dados_*` - Individual service credential files
- **Automatic persistence**: All configuration changes are immediately saved to JSON

### Configuration Structure
```json
{
  "global": {
    "hostname": "server-name",
    "user_email": "user@domain.com", 
    "default_subdomain": "dev",
    "cloudflare_auto_dns": true,
    "network_name": "livchat_network",
    "installation_date": "2025-08-30T18:42:41.980103",
    "version": "2.0",
    "last_updated": "2025-08-30T18:53:04.274607"
  },
  "cloudflare": {
    "api_token": "...",
    "zone_id": "...", 
    "zone_name": "example.com",
    "enabled": true
  },
  "credentials": {},
  "applications": {},
  "dns_records": []
}
```

### Input Pattern Standards
- **Suggestion Pattern**: All user inputs follow `"Field (Enter for 'suggestion' ou digite outro valor): "`
- **State Preservation**: Existing configurations are always suggested as defaults
- **Validation**: Format validation before acceptance (hostname, email, etc.)
- **Optional Fields**: Non-critical configurations can be skipped
- **Consistency**: Same input pattern across all modules for uniform UX

## UI/Design Guidelines

The project follows a consistent visual design pattern across all interfaces (bash setup script and Python TUI menu). These guidelines ensure a professional, cohesive user experience using modern Unicode box drawing and intelligent Python-based layout systems.

### Color Palette

Standard ANSI color codes used throughout the project:

```bash
# Primary colors (Bash)
laranja="\e[38;5;173m"    # Orange - For ASCII art and highlights
verde="\e[32m"            # Green - For success states and selected items
branco="\e[97m"           # Bright white - For focus states and headings
bege="\e[93m"             # Beige - For informational text and legends
vermelho="\e[91m"         # Red - For errors and warnings
cinza="\e[90m"            # Gray - For borders and inactive items
azul="\e[34m"             # Blue - For compatibility (legacy)
reset="\e[0m"             # Reset - Always close color sequences
```

```python
# Python equivalents (module_coordinator.py)
LARANJA = "\033[38;5;173m"  # Orange - For ASCII art and highlights
VERDE = "\033[32m"          # Green - For success states and selected items
BRANCO = "\033[97m"         # Bright white - For focus states and headings
BEGE = "\033[93m"           # Beige - For informational text and legends
VERMELHO = "\033[91m"       # Red - For errors and warnings
CINZA = "\033[90m"          # Gray - For borders and inactive items
RESET = "\033[0m"           # Reset - Always close color sequences
```

### Box Drawing Functions

All UI elements use rounded Unicode box drawing characters for a modern appearance:

#### Border Components
- **Top border**: `╭─────────────────────────────────────────╮`
- **Bottom border**: `╰─────────────────────────────────────────╯`
- **Vertical sides**: `│` (left and right)

#### Standard Functions
```bash
box_top() {
    echo -e "${cinza}╭─────────────────────────────────────────────────────────────────────────────────────────────────────╮${reset}"
}

box_empty() {
    echo -e "${cinza}│                                                                                                     │${reset}"
}

box_bottom() {
    echo -e "${cinza}╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯${reset}"
}
```

#### Python Box Functions

All box drawing in Python modules follows a standardized pattern using Python's native `.center()` method:

```python
def _print_section_box(self, title: str, width: int = None):
    """Standard box printing method - use this pattern in all modules"""
    if width is None:
        terminal_width = self._get_terminal_width()
        width = min(60, terminal_width - 10)  # Small boxes: 60 max width
        # For large boxes (ModuleCoordinator): min(80, terminal_width - 4)
    
    # Remove color codes for accurate centering
    import re
    clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
    
    # Create border
    line = "─" * (width - 1)
    print(f"\n{self.CINZA}╭{line}╮{self.RESET}")
    
    # ALWAYS use native .center() and width - 2
    content_width = width - 2  # Subtract border characters
    centered_clean = clean_title.center(content_width)  # Python native method
    
    # Apply color to title
    colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
    
    print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
    print(f"{self.CINZA}╰{line}╯{self.RESET}")
```

#### Bash Content Functions
```bash
# For centered content (ASCII art, titles, success messages)
box_line_centered() {
    local content="$1"
    local total_width=101  # Internal box width (excluding borders)
    
    # Remove color codes to calculate actual text length
    local clean_content=$(printf "%b" "$content" | sed 's/\x1b\[[0-9;]*m//g')
    local content_length=${#clean_content}
    
    # Calculate padding for perfect centering
    local total_padding=$((total_width - content_length))
    local left_padding=$((total_padding / 2))
    local right_padding=$((total_padding - left_padding))
    
    printf "${cinza}│${reset}"
    printf "%*s" $left_padding ""
    printf "%b" "$content"
    printf "%*s" $right_padding ""
    printf "${cinza}│${reset}\n"
}

# For left-aligned content (menu items, progress indicators)
box_line() {
    local content="$1"
    local clean_content=$(printf "%b" "$content" | sed 's/\x1b\[[0-9;]*m//g')
    local content_length=${#clean_content}
    local right_padding=$((97 - content_length))  # 97 = 99 - 2 spaces
    
    printf "${cinza}│${reset} "
    printf "%b" "$content"
    printf "%*s" $right_padding ""
    printf " ${cinza}│${reset}\n"
}
```

### Design Principles

#### 1. Box Consistency Standards
- **ALWAYS use Python's native `.center()` method** for all Python box centering
- **ALWAYS use `content_width = width - 2`** to account for border characters `│ │`
- **Small boxes**: max width 60 (setup modules)
- **Large boxes**: max width 80 (ModuleCoordinator execution messages)  
- **Colors**: `{self.BEGE}` for small box titles, `{self.LARANJA}` for large box titles

#### 2. ASCII Art Standards
- Always use the **orange color** (`${laranja}`) for ASCII art elements
- Center ASCII art using `box_line_centered()` function
- Surround with empty lines for visual breathing room
- Use consistent letter spacing and style

#### 2. Progress Indicators
- **Success**: `${verde}✓` followed by step description
- **Error**: `${vermelho}✗` followed by step description  
- **In Progress**: `${laranja}◐` for animated states
- **Pending**: `${cinza}○` for not yet started
- Format: `"✓ X/Y - Description"` where X/Y shows progress

#### 3. Interactive Elements
- **Current selection**: `→` arrow prefix with `${branco}` (white) text
- **Selected items**: `●` filled circle with `${verde}` (green) color
- **Unselected items**: `○` empty circle with `${cinza}` (gray) color
- **Focus indication**: White text for current item, gray for others

#### 4. Menu Design Patterns
```bash
# Header with counter
╭─ SETUP LIVCHAT ─────────────────────── Selecionados: 3/34 ─╮
│ ↑/↓ navegar · → marcar (●/○) · Enter executar · Digite para pesquisar         │
│                                                               │

# Content area with proper alignment
│ → ● [1] Config (E-mail, Hostname, Cloudflare, Rede, Timezone)│
│   ○ [2] Instalação do Docker + Swarm                         │
│   ○ [3] Instalação do Traefik (Proxy Reverso)               │

# Footer with legend
│                                                               │
╰───────────────────────────────────────────────────────────────╯
Legenda: ○ = não selecionado · ● = selecionado

# Post-installation menu
Pressione Enter para instalar mais aplicações ou Ctrl+C para encerrar...
```

#### 5. Self-Contained Requirements
- All design functions must be included inline in bash scripts
- No external dependencies or utility files
- Compatible with web installation: `bash <(curl -sSL setup.livchat.ai)`
- All Unicode characters must render correctly in standard terminals

#### 6. Terminal Behavior
- Never clear important status messages (like "VERIFICANDO")
- Use selective line clearing: `\x1b[1A\x1b[2K` for menu redraws
- Preserve terminal history for debugging
- Handle terminal width gracefully (fixed 101-character internal width)

### Usage Examples

#### Setup Script Pattern
```bash
nome_aviso(){
    clear
    echo ""
    box_top
    box_empty
    box_empty
    box_line_centered "${laranja}     ██╗     ██╗██╗   ██╗ ██████╗██╗  ██╗ █████╗ ████████╗     ${reset}"
    box_line_centered "${laranja}     ██║     ██║██║   ██║██╔════╝██║  ██║██╔══██╗╚══██╔══╝     ${reset}"
    box_empty
    box_empty
    box_bottom
    echo ""
}
```

#### Progress Display Pattern
```bash
echo -e "${verde}✓ 1/15 - Fazendo Update${reset}"
echo -e "${verde}✓ 2/15 - Fazendo Upgrade${reset}"  
echo -e "${laranja}◐ 3/15 - Instalando sudo${reset}"
echo -e "${cinza}○ 4/15 - Instalando curl${reset}"
```

### Implementation Notes
- All color variables must be defined at the top of each script
- Always use `${reset}` after colored text to prevent color bleeding
- Test alignment with different terminal widths during development
- Validate Unicode character rendering in various terminal environments
- Follow the 101-character internal width standard for consistency