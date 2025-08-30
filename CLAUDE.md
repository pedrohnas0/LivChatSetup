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
   - `interactive_menu.py`: Main menu interface
   - `module_coordinator.py`: Module mapping and execution coordinator
   - `portainer_api.py`: Portainer API integration for stack deployment
   - `template_engine.py`: Jinja2 template processing
   - `cloudflare_api.py`: DNS automation integration

### Key Classes
- **BaseSetup**: Abstract base class for all setup modules with common functionality
- **PortainerAPI**: Handles Docker Swarm deployment via Portainer API
- **InteractiveMenu**: Manages the interactive CLI menu system
- **ModuleCoordinator**: Maps and executes setup modules

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
1. Validate prerequisites (Docker, Swarm, network, databases)
2. Collect user inputs (domain, email, passwords)
3. Generate secure keys and passwords
4. Optionally setup DNS via Cloudflare API
5. Deploy stack via `PortainerAPI.deploy_service_complete()`
6. Wait for services to be healthy
7. Save credentials to `/root/dados_vps/dados_<service>`

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

### Database Sharing
- Directus reuses Chatwoot's PostgreSQL database by design
- Template uses `DB_DATABASE=chatwoot` instead of creating separate DB
- Simplifies infrastructure and reduces operational overhead

### Service Dependencies
- Basic setup → Hostname → Docker+Swarm → Traefik → Portainer is the required sequence
- Applications can be installed in any order after infrastructure is ready
- PostgreSQL with PgVector is shared across multiple applications

### Logging and Monitoring
- Structured logging with timestamps and log levels
- File rotation (10MB, 5 backups)
- Console output with color coding
- Service health monitoring via Portainer API

### Current Status
- Infrastructure modules: Complete and production-ready
- Database modules: Complete (Redis, PostgreSQL+PgVector, MinIO)
- Applications: Chatwoot and Directus are production-ready
- Evolution API v2: Available but in testing
- Other applications: Available via menu but may need testing

## UI/Design Guidelines

The project follows a consistent visual design pattern across all interfaces (bash setup script and Python TUI menu). These guidelines ensure a professional, cohesive user experience.

### Color Palette

Standard ANSI color codes used throughout the project:

```bash
# Primary colors
laranja="\e[38;5;173m"    # Orange - For ASCII art and highlights
verde="\e[32m"            # Green - For success states and selected items
branco="\e[97m"           # Bright white - For focus states and headings
bege="\e[93m"             # Beige - For informational text and legends
vermelho="\e[91m"         # Red - For errors and warnings
cinza="\e[90m"            # Gray - For borders and inactive items
azul="\e[34m"             # Blue - For compatibility (legacy)
reset="\e[0m"             # Reset - Always close color sequences
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

#### Content Functions
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

#### 1. ASCII Art Standards
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
╭─ SETUP LIVCHAT ─────────────────────── Selecionados: 3/35 ─╮
│ ↑/↓ navegar · → marcar (●/○) · Enter duplo executar · Esc voltar              │
│                                                               │

# Content area with proper alignment
│ → ● [1] Configuração Básica do Sistema                       │
│   ○ [2] Configuração de Hostname                             │
│   ○ [3] Instalação do Docker + Swarm                         │

# Footer with legend
│                                                               │
╰───────────────────────────────────────────────────────────────╯
Legenda: ○ = não selecionado · ● = selecionado
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