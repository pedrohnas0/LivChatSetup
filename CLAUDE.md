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

### Critical: Domain Suggestion Pattern
**NEVER use hostname for domain suggestions** - this causes domains like `edt.dev.localhost` instead of `edt.dev.livchat.ai`.

#### ✅ CORRECT Pattern
Use ConfigManager's built-in method that uses Cloudflare zone_name:
```python
# In setup modules - PREFERRED METHOD
suggested_domain = self.config.suggest_domain("app_name")  # Uses zone_name automatically
```

#### ✅ CORRECT Pattern (Manual)
If implementing custom domain suggestion logic, use zone_name:
```python
def _get_domain_suggestion(self, domain_key: str, subdomain_prefix: str) -> str:
    # Check existing config first
    existing_config = self.config.get_app_config('app_name')
    if existing_config and domain_key in existing_config:
        return existing_config[domain_key]
    
    # Use Cloudflare zone_name (NOT hostname)
    cloudflare_config = self.config.get_cloudflare_config()
    zone_name = cloudflare_config.get('zone_name', '')
    default_subdomain = self.config.get_default_subdomain() or 'dev'
    
    if zone_name:
        return f"{subdomain_prefix}.{default_subdomain}.{zone_name}"  # ✅ CORRECT
    else:
        hostname = self.config.get_hostname() or 'localhost'
        return f"{subdomain_prefix}.{default_subdomain}.{hostname}"  # Fallback only
```

#### ❌ WRONG Pattern
```python
# DON'T DO THIS - causes localhost domains
hostname = self.config.get_hostname() or 'localhost'  # ❌ WRONG
return f"{subdomain_prefix}.{default_subdomain}.{hostname}"
```

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
- **Database modules**: ✅ **Redis e PostgreSQL refatorados e funcionais** 
- **Applications**: ✅ **N8N completamente refatorado com sessão de sucesso**
- **Chatwoot/Directus**: Parcialmente refatorados, funcionais mas ainda dependem de alguns `dados_vps`
- **ConfigManager Migration**: **8/17 módulos refatorados (47% concluído)**
- **Interactive Experience**: Full TUI menu with search, multi-selection, and post-install options
- **Configuration Persistence**: Migração ativa para livchat-config.json centralizado
- **Success Sessions**: N8N implementado com padrão Portainer para configuração de conta
- **Domain Suggestions**: Corrigido para usar zone_name do Cloudflare (não hostname)

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

# CHECKLIST DE REFATORAÇÃO: MIGRAÇÃO PARA ConfigManager

## Status da Refatoração

### ✅ Módulos Refatorados (Padrão Correto)
- **[01] basic_setup.py** - Configuração básica (e-mail, hostname, DNS, rede, timezone)
- **[02] smtp_setup.py** - Configuração SMTP para aplicações 
- **[05] portainer_setup.py** - Gerenciador Docker Portainer
- **[06] redis_setup.py** - Cache/Session Store ✨ **REFATORADO**
- **[07] postgres_setup.py** - Banco relacional ✨ **REFATORADO**
- **[12] n8n_setup.py** - Workflow Automation ✨ **REFATORADO + SESSÃO DE SUCESSO**
- **[17] cleanup_setup.py** - Limpeza completa do ambiente
- **[XX] user_setup.py** - Dados do usuário (módulo oculto) ✨ **NOVO**

### ❌ Módulos Pendentes de Refatoração (9 módulos)
- **[08] pgvector_setup.py** - Banco vetorial
- **[09] minio_setup.py** - S3 Compatible Storage
- **[10] chatwoot_setup.py** - Customer Support Platform (parcialmente refatorado)
- **[11] directus_setup.py** - Headless CMS
- **[13] grafana_setup.py** - Stack de monitoramento
- **[14] gowa_setup.py** - WhatsApp API Multi Device
- **[15] livchatbridge_setup.py** - Webhook Connector
- **[16] passbolt_setup.py** - Password Manager
- **[18] evolution_setup.py** - WhatsApp API v2

### ❌ Arquivos Utilitários (2 arquivos)
- **utils/module_coordinator.py** - 3 referências `dados_vps`
- **utils/cloudflare_api.py** - 2 referências `dados_vps`

## Padrão de Refatoração ConfigManager

### 1. Importação e Inicialização
```python
# Adicionar import no topo do arquivo
from utils.config_manager import ConfigManager

# No construtor __init__
def __init__(self, config_manager: ConfigManager = None):
    super().__init__()
    self.config = config_manager or ConfigManager()
```

### 2. Métodos ConfigManager Utilizados

#### Métodos de Configuração de Aplicação
```python
# Salvar configuração da aplicação
self.config.save_app_config(app_name, config_data)

# Salvar credenciais da aplicação  
self.config.save_app_credentials(app_name, credentials)

# Obter email do usuário
user_email = self.config.get_user_email()

# Obter configurações globais
hostname = self.config.get_global_config().get('hostname')
network_name = self.config.get_global_config().get('network_name')
```

#### Métodos de Dados Específicos
```python
# Obter configurações de uma aplicação
app_config = self.config.get_app_config(app_name)
app_creds = self.config.get_app_credentials(app_name)

# Verificar se aplicação está configurada
is_configured = self.config.is_app_configured(app_name)
```

### 3. Estrutura JSON no ConfigManager

```json
{
  "global": {
    "hostname": "server-name",
    "user_email": "user@domain.com",
    "default_subdomain": "dev", 
    "network_name": "livchat_network"
  },
  "applications": {
    "postgres": {
      "domain": "db.domain.com",
      "configured_at": "2025-08-31T10:30:00",
      "version": "16"
    }
  },
  "credentials": {
    "postgres": {
      "password": "senha_gerada",
      "username": "postgres",
      "database": "postgres",
      "created_at": "2025-08-31T10:30:00"
    }
  }
}
```

### 4. Sistema de Sugestões Inteligentes

```python
# Padrão para inputs com sugestões do ConfigManager
def _get_domain_input(self, service_name: str) -> str:
    """Solicita domínio com sugestão inteligente do ConfigManager"""
    existing_config = self.config.get_app_config(service_name)
    suggestion = existing_config.get('domain', f"{service_name}.dev.{self.config.get_global_config().get('hostname', 'localhost')}")
    
    domain = input(f"Domínio do {service_name.title()} (Enter para '{suggestion}' ou digite outro valor): ").strip()
    return domain if domain else suggestion
```

## Pontos de Ajuste Específicos por Arquivo

### ✅ redis_setup.py - **REFATORADO COMPLETAMENTE**
**✅ Alterações implementadas:**
- ✅ `ConfigManager` integrado no construtor
- ✅ Escrita manual de arquivo substituída por `save_app_credentials()`
- ✅ Logs atualizados para referenciar ConfigManager
- ✅ Migração completa para configuração centralizada

### ✅ postgres_setup.py - **REFATORADO COMPLETAMENTE**
**✅ Alterações implementadas:**
- ✅ `ConfigManager` integrado no construtor
- ✅ Bloco de escrita para arquivo substituído por métodos ConfigManager
- ✅ Sistema de geração de senhas seguras via ConfigManager
- ✅ Configuração e credenciais salvas separadamente
- ✅ Logs de confirmação atualizados

### 📦 pgvector_setup.py
**Linhas para alterar:**
- `L218-221`: Escrita de credenciais → `save_app_credentials('pgvector', credentials)`
- `L263`: Log de confirmação → Atualizar mensagem

**Refatoração necessária:**
1. Mesmo padrão do postgres_setup.py
2. Verificar dependência com PostgreSQL via ConfigManager

### 📦 minio_setup.py
**Linhas para alterar:**
- `L260-263`: Bloco escrita arquivo → `save_app_credentials('minio', credentials)`
- `L312`: Log de confirmação → Atualizar mensagem

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Sistema de sugestões para access_key e secret_key
3. Migração de dados antigos

### 📦 chatwoot_setup.py
**Linhas para alterar:**
- `L91`: `with open("/root/dados_vps/dados_pgvector", 'r') as f:` → `self.config.get_app_credentials('pgvector')`
- `L177`: `self.config.save_app_config('chatwoot', config_data)` (já parcialmente implementado)
- `L185`: `self.config.save_app_credentials('chatwoot', credentials)` (já parcialmente implementado)

**Refatoração necessária:**
1. Remover leitura manual de arquivo dados_pgvector
2. Usar `get_app_credentials('pgvector')` para obter senha do banco
3. Sistema de sugestões para domínio Chatwoot

### 📦 directus_setup.py
**Linhas para alterar:**
- `L84`: `with open("/root/dados_vps/dados_pgvector", 'r') as f:` → `self.config.get_app_credentials('pgvector')`

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Substituir leitura manual por métodos ConfigManager
3. Implementar salvamento de credenciais Directus
4. Sistema de sugestões para configurações

### ✅ n8n_setup.py - **REFATORADO COMPLETAMENTE**
**✅ Alterações implementadas:**
- ✅ `ConfigManager` integrado no construtor
- ✅ Todas as leituras manuais de arquivos substituídas por métodos ConfigManager
- ✅ Sistema de sugestões para domínios N8N (usa Cloudflare zone_name)
- ✅ Database `n8n_queue` dedicada com limpeza automática
- ✅ **Sessão de sucesso** implementada seguindo padrão Portainer
- ✅ **Configuração de conta** com credenciais sugeridas (email + senha 64 chars)
- ✅ **Suporte a primeiro/último nome** (condicional - só se configurado)
- ✅ Migração completa para ConfigManager centralizado

**🎯 Funcionalidades especiais:**
- **Limpeza de database**: Remove databases antigas para evitar conflitos de migração
- **Domain suggestion fix**: Usa `zone_name` em vez de `hostname` 
- **Success session**: Interface igual ao Portainer para configurar conta inicial
- **User data**: Integração com `user_setup.py` para dados pessoais opcionais

### 📦 evolution_setup.py
**Linhas para alterar:**
- `L149`: `creds_path = "/root/dados_vps/dados_postgres"` → `self.config.get_app_credentials('postgres')`
- `L169`: `creds_path = "/root/dados_vps/dados_redis"` → `self.config.get_app_credentials('redis')`

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Substituir leituras de arquivos por métodos ConfigManager
3. Implementar salvamento de credenciais Evolution
4. Sistema de sugestões para configurações

### 📦 grafana_setup.py
**Linhas para alterar:**
- `L320-322`: Bloco escrita arquivo → `self.config.save_app_credentials('grafana', credentials)`

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Sistema de sugestões para credenciais admin
3. Integração com bases de dados via ConfigManager

### 📦 gowa_setup.py
**Linhas para alterar:**
- `L140`: Log de credenciais salvas → Atualizar mensagem
- `L169`: `with open("/root/dados_vps/dados_gowa", 'w', encoding='utf-8') as f:` → `self.config.save_app_credentials('gowa', credentials)`

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Substituir escrita manual por métodos ConfigManager
3. Sistema de sugestões para token WhatsApp

### 📦 passbolt_setup.py
**Linhas para alterar:**
- `L8`: Comentário sobre salvamento → Atualizar para ConfigManager
- `L29`: `self.credentials_path = "/root/dados_vps/dados_passbolt"` → Remover (usar ConfigManager)
- `L170, L296, L459, L487`: Caminhos debug logs → Manter inalterado (logs de debug)
- `L586`: Mensagem sobre logs debug → Manter inalterado

**Refatoração necessária:**
1. Adicionar ConfigManager no construtor
2. Remover `credentials_path` e usar ConfigManager
3. Implementar salvamento via `save_app_credentials()`
4. Sistema de sugestões para configurações Passbolt

### 📦 livchatbridge_setup.py
**Refatoração necessária:**
1. Verificar se existe referência a `dados_vps` (não encontrada na análise)
2. Implementar ConfigManager se não existir
3. Sistema de salvamento de credenciais

### 🔧 utils/module_coordinator.py
**Linhas para alterar:**
- `L402`: `return "/root/dados_vps/dados_network"` → Usar ConfigManager para network
- `L439`: `return "/root/dados_vps/dados_vps"` → Usar ConfigManager para dados VPS 
- `L489`: `return "/root/dados_vps/dados_hostname"` → Usar ConfigManager para hostname

**Refatoração necessária:**
1. Integrar com ConfigManager para obter dados globais
2. Substituir retornos de caminhos por métodos ConfigManager
3. Manter compatibilidade com módulos ainda não refatorados

### 🔧 utils/cloudflare_api.py
**Linhas para alterar:**
- `L78`: `old_file = "/root/dados_vps/dados_cloudflare"` → Migração via ConfigManager
- `L389-391`: Obtenção do host Portainer → `self.config.get_app_config('portainer')`

**Refatoração necessária:**
1. Integrar com ConfigManager para configurações Cloudflare
2. Substituir leitura de `dados_portainer` por ConfigManager
3. Sistema de migração de configurações antigas

## Comandos de Teste Pós-Refatoração

### Verificação de Referências
```bash
# Verificar se ainda existem referências a dados_vps
grep -r "dados_vps" setup/ utils/ --exclude="*.md"

# Verificar importações ConfigManager
grep -r "from utils.config_manager import ConfigManager" setup/

# Verificar métodos ConfigManager utilizados  
grep -r "\.save_app_" setup/
grep -r "\.get_app_" setup/
```

### Teste de Migração
```bash
# Executar módulo refatorado para teste
sudo python3 main.py --verbose

# Verificar estrutura do livchat-config.json
cat /root/livchat-config.json | jq '.'

# Verificar se dados_vps ainda existe (deve estar vazio após migração)
ls -la /root/dados_vps/
```

## ✨ Recursos Implementados Recentemente

### 🎯 Sessão de Sucesso (Success Session Pattern)
**Implementado no N8N, baseado no padrão do Portainer:**
- **Tela de sucesso** com informações da instalação
- **Credenciais sugeridas** automáticas (email + senha 64 caracteres)
- **Confirmação interativa** com padrão Enter/Valor/ESC
- **Dados de usuário opcionais** (primeiro/último nome)
- **Resumo final** com instruções de uso
- **Integração ConfigManager** para persistir dados da conta

### 🔧 Domain Suggestion Fix
**Correção crítica na sugestão de domínios:**
- **Problema**: Domínios sugeridos como `app.dev.localhost` 
- **Solução**: Usar `zone_name` do Cloudflare (ex: `app.dev.livchat.ai`)
- **Pattern correto**: `self.config.suggest_domain("app_name")` 
- **Fallback seguro**: hostname apenas se zone_name não disponível

### 👤 User Setup Module
**Novo módulo oculto para dados pessoais:**
- **Arquivo**: `setup/user_setup.py` (sem número no menu)
- **Função**: Gerenciar primeiro nome e último nome
- **Integração**: Usado por outras aplicações que necessitam
- **Comportamento**: Enter aceita sugestão, ESC pula campo
- **Storage**: Dados salvos em `livchat-config.json`

### 🛠️ Database Cleanup
**N8N com limpeza automática de databases:**
- **Remove databases antigas** antes de criar nova
- **Desconecta usuários ativos** automaticamente  
- **Cria database `n8n_queue` limpa** para evitar conflitos
- **Suporte a migração** sem conflitos de schema

## Notas Importantes

1. **Migração Automática**: Todos os módulos refatorados implementam migração automática dos arquivos `dados_vps` existentes
2. **Compatibilidade**: Durante período de transição, alguns módulos ainda dependem de `dados_vps` 
3. **Sistema de Sugestões**: Implementado com sugestões inteligentes baseadas em configurações existentes
4. **Timestamping**: Adicionado `created_at` e `configured_at` em todas as configurações salvas
5. **Domain Corrections**: Corrigido para usar zone_name do Cloudflare em todos os módulos refatorados
6. **Success Sessions**: N8N implementa padrão completo de sessão pós-instalação
7. **User Data**: Sistema opcional e condicional para dados pessoais do usuário