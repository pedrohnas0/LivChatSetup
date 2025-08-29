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