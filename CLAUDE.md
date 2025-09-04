# CLAUDE.md

AI assistant context for LivChatSetup project - modular Linux server configuration system.

> **🔄 Migration Status**: 50% complete (9/18 modules migrated to ConfigManager)  
> **Priority**: Focus on `pgvector_setup.py` and `directus_setup.py` - they block other modules

## Quick Start

```bash
# Local execution with interactive menu
sudo python3 main.py [--verbose|--quiet]

# Web installation
bash <(curl -sSL setup.livchat.ai) [--verbose|--quiet]
```

## Architecture

### Core Files
- `main.py` - Entry point with prerequisite validation
- `config.py` - Global configurations and logging
- `livchat-config.json` - Persistent configuration storage

### Directory Structure
```
setup/              # Setup modules inheriting from BaseSetup
templates/          # Docker Compose Jinja2 templates  
utils/              # Core utilities and coordinators
  ├── interactive_menu.py    # TUI menu with Docker monitoring
  ├── module_coordinator.py  # Module execution orchestrator
  ├── config_manager.py      # Centralized config management
  ├── docker_monitor.py      # Real-time service monitoring
  └── portainer_api.py       # Stack deployment via Portainer
```

## Key Features

### Interactive Menu System
- **Real-time monitoring**: CPU, Memory, and replica status
- **Multi-selection TUI**: Select multiple apps for batch installation
- **Search filtering**: Type to filter 34+ available modules
- **Docker integration**: Live service status with animated spinners

### Module System
Each module in `setup/` follows this pattern:
```python
class ServiceSetup(BaseSetup):
    def validate_prerequisites(self) -> bool
    def run(self) -> bool
```

### Configuration Management (ConfigManager)
Centralized JSON configuration at `/root/livchat-config.json`:
```json
{
  "global": {
    "hostname": "server",
    "user_email": "user@domain.com",
    "default_subdomain": "dev",
    "network_name": "livchat_network"
  },
  "cloudflare": {
    "zone_name": "domain.com",
    "zone_id": "...",
    "api_token": "..."
  },
  "applications": {},
  "credentials": {}
}
```

## Critical Patterns

### Domain Suggestions
**Always use Cloudflare zone_name, never hostname:**
```python
# ✅ CORRECT
suggested_domain = self.config.suggest_domain("app_name")

# ❌ WRONG - causes localhost domains
hostname = self.config.get_hostname()
return f"{app}.{hostname}"  # Don't do this!
```

### Template Standards
- Use `{{ network_name }}` for Docker network reference
- Include Traefik labels for SSL/routing
- Parametrize all credentials and domains

### Deployment Flow
1. Interactive menu selection
2. Basic setup (email, hostname, DNS, network)
3. Infrastructure (Docker, Traefik, Portainer)
4. Applications with auto-generated credentials
5. Save to both ConfigManager and `/root/dados_vps/`

## UI/Design Standards

### Colors (Python)
```python
LARANJA = "\033[38;5;173m"  # Orange - ASCII art
VERDE = "\033[32m"          # Green - success/selected
BRANCO = "\033[97m"         # White - focus/headings
BEGE = "\033[93m"           # Beige - info text
VERMELHO = "\033[91m"       # Red - errors
CINZA = "\033[90m"          # Gray - borders/inactive
```

### Box Drawing Pattern
```python
def _print_section_box(self, title: str, width: int = 60):
    line = "─" * (width - 1)
    print(f"\n{self.CINZA}╭{line}╮{self.RESET}")
    
    # Always use .center() with width - 2
    content_width = width - 2
    centered = title.center(content_width)
    
    print(f"{self.CINZA}│{self.BEGE}{centered}{self.RESET}{self.CINZA}│{self.RESET}")
    print(f"{self.CINZA}╰{line}╯{self.RESET}")
```

### Menu Layout (92 chars width)
```
╭─ SETUP LIVCHAT ──────────────────── Selecionados: 3/34 ─╮
│ ↑/↓ navegar · → marcar · Enter executar · Digite pesquisar │
│ APLICAÇÃO                                STATUS   CPU    MEM │
│ > ● [1] Config                           2/2     0.5%   12M │
╰───────────────────────────────────────────────────────────╯
```

## Module Status

### Infrastructure (Required Order)
1. ✅ `basic_setup` - Email, hostname, DNS, network, timezone
2. ✅ `docker_setup` - Docker + Swarm initialization  
3. ✅ `traefik_setup` - Reverse proxy with SSL
4. ✅ `portainer_setup` - Docker management UI

### Databases
- ✅ `redis_setup` - In-memory cache (ConfigManager integrated)
- ✅ `postgres_setup` - Relational DB (ConfigManager integrated)
- ⚠️ `pgvector_setup` - Vector DB (needs refactoring)
- ⚠️ `minio_setup` - S3 storage (needs refactoring)

### Applications
- ✅ `n8n_setup` - Workflow automation (with success session)
- ✅ `smtp_setup` - Email configuration
- ⚠️ `chatwoot_setup` - Customer support (partial refactor)
- ⚠️ `directus_setup` - Headless CMS (needs refactoring)
- ⚠️ `evolution_setup` - WhatsApp API (needs refactoring)
- Plus 9 more modules pending ConfigManager migration

## Development Guidelines

### Adding New Services
1. Create `setup/<service>_setup.py` inheriting from `BaseSetup`
2. Create `templates/docker-compose/<service>.yaml.j2`
3. Import in `utils/module_coordinator.py`
4. Add to menu in `utils/interactive_menu.py`

### Testing
```bash
# Check for legacy references
grep -r "dados_vps" setup/ utils/ --exclude="*.md"

# Verify ConfigManager usage
grep -r "ConfigManager" setup/ | wc -l

# Test installation
sudo python3 main.py --verbose
```

### Security Notes
- Root privileges required
- Auto-generated 64-char passwords
- HTTPS via Let's Encrypt
- Credentials at `/root/dados_vps/` (legacy) and `livchat-config.json`

## Recent Updates

### ✨ Docker Monitor Integration
- Real-time CPU/Memory monitoring
- Service replica status
- Animated spinners at 100ms intervals
- Thread-safe caching (2s updates)

### 🎯 N8N Success Session
- Post-install configuration UI
- Auto-suggested credentials
- First/last name support
- Database cleanup for migrations

### 🔧 ConfigManager Migration
- 8/17 modules refactored (47%)
- Automatic legacy data migration
- Centralized configuration persistence
- Smart domain suggestions using Cloudflare

## 🚀 CHECKLIST COMPLETA DE REFATORAÇÃO

### Status Geral: 12/20 módulos (60% completos) | 8 módulos pendentes

### 📊 RESUMO DE STATUS

**✅ Componentes Core Refatorados:**
- **cloudflare_api.py**: v4.0 - APENAS Global API Key
- **module_coordinator.py**: 100% ConfigManager
- **config_manager.py**: Migração automática funcional
- **Registros DNS**: CNAME por padrão (exceto Portainer)

**🎯 Meta Final:**
- Eliminar 100% das referências a `/root/dados_vps/`
- Todos os dados em `/root/livchat-config.json`
- Padrão visual unificado em todos os módulos
- Integração completa com Portainer API

### 🛠️ COMPONENTES UTILITÁRIOS

#### ✅ Totalmente Refatorados
- [ ] ✅ **cloudflare_api.py**
  - [x] ConfigManager integrado
  - [x] Global API Key apenas
  - [x] Zero dados_vps
  - [x] CNAME por padrão
  
- [ ] ✅ **module_coordinator.py**
  - [x] ConfigManager integrado
  - [x] Métodos legacy deprecated
  - [x] Swarm check corrigido
  - [x] Zero dados_vps

### 📦 MÓDULOS DE APLICAÇÃO

#### 🏗️ INFRAESTRUTURA BÁSICA
- [ ] ✅ **basic_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern implementado
  - [x] Zero dados_vps
  - [x] Cloudflare com email
  
- [ ] ✅ **docker_setup.py**
  - [x] ConfigManager integrado
  - [x] Swarm sempre inicializado
  - [x] Zero dados_vps
  
- [ ] ✅ **traefik_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern básico
  - [x] Zero dados_vps
  - [x] SSL automático
  
- [ ] ✅ **portainer_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern completo
  - [x] Zero dados_vps
  - [x] Registro A (único)
  - [x] API de deploy configurada
  
- [ ] ✅ **smtp_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern completo
  - [x] Zero dados_vps
  - [x] Config centralizada
  
- [ ] ⚠️ **hostname_setup.py**
  - [x] Zero dados_vps
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  
- [ ] ⚠️ **cleanup_setup.py**
  - [x] Zero dados_vps
  - [ ] ConfigManager não necessário
  - [ ] Visual pattern pendente

#### 💾 BANCOS DE DADOS

- [ ] ✅ **postgres_setup.py**
  - [x] ConfigManager integrado
  - [x] Zero dados_vps
  - [x] Portainer API
  - [ ] Visual pattern pendente
  
- [ ] ✅ **redis_setup.py**
  - [x] ConfigManager integrado
  - [x] Zero dados_vps
  - [x] Portainer API
  - [ ] Visual pattern pendente
  
- [ ] ⚠️ **pgvector_setup.py**
  - [x] ConfigManager parcial
  - [x] Mantém legacy para compatibilidade
  - [ ] Visual pattern pendente
  - [ ] ❌ 3 refs dados_vps

#### 🚀 APLICAÇÕES PRINCIPAIS

- [ ] ✅ **n8n_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern completo
  - [x] Zero dados_vps
  - [x] SMTP centralizado
  - [x] Success session
  - [x] CNAME configurado
  
- [ ] ⚠️ **chatwoot_setup.py**
  - [x] ConfigManager integrado
  - [x] Visual pattern completo
  - [x] SMTP centralizado
  - [x] Success session
  - [ ] ❌ 1 ref dados_vps
  
- [ ] ⚠️ **directus_setup.py**
  - [x] ConfigManager integrado
  - [ ] Visual pattern pendente
  - [x] Domain suggestions
  - [ ] ❌ 1 ref dados_vps (pgvector)
  
- [ ] ❌ **evolution_setup.py**
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  - [ ] SMTP pendente
  - [ ] ❌ 2 refs dados_vps (postgres/redis)
  
- [ ] ❌ **minio_setup.py**
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  - [ ] ❌ 4 refs dados_vps
  
- [ ] ❌ **grafana_setup.py**
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  - [ ] ❌ 3 refs dados_vps
  
- [ ] ❌ **passbolt_setup.py**
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  - [ ] ❌ 10 refs dados_vps (mais complexo)
  
- [ ] ❌ **gowa_setup.py**
  - [ ] ConfigManager pendente
  - [ ] Visual pattern pendente
  - [ ] ❌ 3 refs dados_vps
  
- [ ] ⚠️ **livchatbridge_setup.py**
  - [x] ConfigManager parcial
  - [x] Visual pattern básico
  - [x] Zero dados_vps
  - [ ] Integração completa pendente

### 📋 PADRÕES DE REFATORAÇÃO OBRIGATÓRIOS

#### 📋 CHECKLIST DE REFATORAÇÃO POR MÓDULO

Cada módulo deve implementar TODOS os seguintes padrões:

- [ ] **1. ConfigManager**
  - [ ] Importar ConfigManager
  - [ ] Passar no construtor
  - [ ] Usar `save_app_config()` e `save_app_credentials()`
  - [ ] Eliminar TODOS os `/root/dados_vps/` writes
  - [ ] Implementar migração automática se necessário

- [ ] **2. Padrão Visual**
  - [ ] Definir cores (LARANJA, VERDE, BRANCO, etc.)
  - [ ] Implementar `_print_section_box()`
  - [ ] Implementar `get_user_input()` com sugestões
  - [ ] ASCII art consistente

- [ ] **3. Integração SMTP**
  - [ ] NUNCA pedir credenciais SMTP
  - [ ] Usar `config.get_app_config("smtp")`
  - [ ] Oferecer configurar se não existir

- [ ] **4. DNS Inteligente**
  - [ ] Usar `config.suggest_domain()`
  - [ ] CNAME por padrão (exceto Portainer)
  - [ ] Integração com Cloudflare API

- [ ] **5. Deploy via Portainer**
  - [ ] Usar PortainerAPI para deploy
  - [ ] Templates Jinja2 padronizados
  - [ ] Labels Traefik corretas

- [ ] **6. Success Session**
  - [ ] Mostrar URL de acesso
  - [ ] Sugerir credenciais inteligentes
  - [ ] Coletar confirmação do usuário
  - [ ] Salvar no ConfigManager

### 🎯 PRIORIDADES DE REFATORAÇÃO

#### 🔴 PRIORIDADE ALTA (Bloqueiam outros módulos)

1. **evolution_setup.py** (2 refs dados_vps)
   - L149-156: Ler senha postgres → ConfigManager
   - L169-176: Ler senha redis → ConfigManager
   - Adicionar padrão visual completo
   - Integrar SMTP centralizado

2. **directus_setup.py** (1 ref dados_vps) 
   - L84: Ler credenciais pgvector → ConfigManager
   - Adicionar padrão visual completo
   - Já tem domain suggestions ✅

3. **pgvector_setup.py** (3 refs dados_vps)
   - Completar migração ConfigManager
   - Remover legacy compatibility
   - Adicionar padrão visual

#### 🟡 PRIORIDADE MÉDIA (Independentes)

4. **minio_setup.py** (4 refs dados_vps)
   - L260-263: Salvar credenciais → ConfigManager
   - Adicionar domain suggestions
   - Adicionar padrão visual completo

5. **grafana_setup.py** (3 refs dados_vps)
   - L319-322: Salvar credenciais → ConfigManager
   - Adicionar monitoring integrations
   - Adicionar padrão visual completo

6. **gowa_setup.py** (3 refs dados_vps)
   - L169: Salvar credenciais → ConfigManager
   - Adicionar padrão visual completo
   - Integrar com Evolution API

#### 🟢 PRIORIDADE BAIXA (Complexos)

7. **passbolt_setup.py** (10 refs dados_vps - MAIS COMPLEXO)
   - L29: Remover credentials_path
   - L168, 247, 294, 458, 486, 586: Múltiplas escritas
   - Requer refatoração completa
   - Debug logs precisam migração

8. **chatwoot_setup.py** (1 ref dados_vps)
   - Finalizar remoção última referência
   - Visual pattern já OK ✅
   - SMTP já integrado ✅

### 📊 ESTATÍSTICAS DA REFATORAÇÃO

**Módulos Totais:** 20
- ✅ **Completos:** 8 (40%)
- ⚠️ **Parciais:** 4 (20%)
- ❌ **Pendentes:** 8 (40%)

**Referências dados_vps:**
- Total: 27 referências em 8 arquivos
- passbolt_setup.py: 10 refs (mais complexo)
- minio_setup.py: 4 refs
- pgvector_setup.py: 3 refs
- grafana_setup.py: 3 refs
- gowa_setup.py: 3 refs
- evolution_setup.py: 2 refs
- directus_setup.py: 1 ref
- chatwoot_setup.py: 1 ref

### 🔧 ARQUIVOS UTILITÁRIOS

#### ✅ `utils/module_coordinator.py` - **REFATORAÇÃO COMPLETA**
**Status: CONCLUÍDO** - Todos os métodos migrados para ConfigManager

**Métodos Refatorados:**
- ✅ `_load_network_name()` - Agora usa ConfigManager com migração automática
- ✅ `_save_network_name()` - Salva direto no ConfigManager  
- ✅ `_load_hostname()` - Usa ConfigManager com fallback para migração
- ✅ `_save_hostname()` - Salva direto no ConfigManager
- ✅ `_read_dados_vps_value()` - Mapeia para ConfigManager (deprecated)
- ✅ `_upsert_dados_vps()` - Usa ConfigManager internamente (deprecated)

**Funcionalidades:**
- Migração automática de arquivos antigos na primeira leitura
- Todos os dados salvos em `/root/livchat-config.json`
- Métodos deprecated mantidos para compatibilidade
- Zero escrita em `/root/dados_vps/`

#### ✅ `utils/cloudflare_api.py` - **REFATORAÇÃO COMPLETA (v4.0 - Global API Key Only)**
**Status: CONCLUÍDO** - Módulo usa APENAS Global API Key como no design original

**Funcionalidades Implementadas:**
- ✅ Suporte **EXCLUSIVO** para **Global API Key + Email** (design original)
- ✅ Autenticação via headers `X-Auth-Email` e `X-Auth-Key`
- ✅ Integração total com ConfigManager
- ✅ Método único: `setup_credentials()` com email obrigatório
- ✅ Teste de conexão validando credenciais Global API Key
- ✅ Gestão completa de DNS (A, CNAME, atualizações)
- ✅ Auto-detecção de IP público
- ✅ Sugestão inteligente de domínios via ConfigManager
- ✅ Factory function `get_cloudflare_api()` simplificada

**Mudanças Principais:**
1. **Removido** todas as referências a `/root/dados_vps/`
2. **Removido** suporte a API Tokens - APENAS Global API Key
3. **Email obrigatório** salvo no ConfigManager junto com API Key
4. **Portainer domain** agora vem do ConfigManager
5. **Autenticação única** como no repositório original

## 🎯 Complete Refactoring Requirements

### Core Principles
1. **ConfigManager Integration** - ALL modules must use ConfigManager
2. **SMTP Centralization** - NEVER ask for SMTP credentials, use `smtp_setup.py`
3. **Visual Consistency** - Follow N8N's design pattern exactly
4. **Domain Intelligence** - Use `config.suggest_domain()` for all domains
5. **Dependency Management** - Pass ConfigManager to all child modules
6. **Success Session** - Post-install configuration UI for initial account setup

### Visual Design Standards (N8N Pattern)

#### Color Definitions (REQUIRED in all modules)
```python
# Cores para interface (seguindo padrão do projeto)
LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
VERDE = "\033[32m"          # Green - Para success states e selected items
BRANCO = "\033[97m"         # Bright white - Para focus states e headings
BEGE = "\033[93m"           # Beige - Para informational text e legends
VERMELHO = "\033[91m"       # Red - Para errors e warnings
CINZA = "\033[90m"          # Gray - Para borders e inactive items
RESET = "\033[0m"           # Reset - Always close color sequences
```

#### Required Helper Methods
```python
def _get_terminal_width(self) -> int:
    """Obtém largura do terminal de forma segura"""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        return 80  # Fallback

def _print_section_box(self, title: str, width: int = 60):
    """Cria box de seção menor seguindo padrão do projeto"""
    # Implementation from N8N...

def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None) -> str:
    """Coleta entrada do usuário com sugestão opcional"""
    # Implementation from N8N...
```

### SMTP Integration Pattern

#### NEVER Ask for SMTP Credentials!
```python
# ❌ WRONG - Never do this!
smtp_email = input("Digite o email SMTP: ")
smtp_password = input("Digite a senha SMTP: ")

# ✅ CORRECT - Get from ConfigManager
smtp_config = self.config.get_app_config("smtp")
if not smtp_config or not smtp_config.get("configured", False):
    self._print_section_box("⚠️  SMTP NÃO CONFIGURADO")
    # Offer to configure SMTP...
    from setup.smtp_setup import SMTPSetup
    smtp_setup = SMTPSetup(config_manager=self.config)
    if not smtp_setup.run():
        return None
    smtp_config = self.config.get_app_config("smtp")

# Use SMTP config
smtp_email = smtp_config['sender_email']
smtp_user = smtp_config['smtp_username']
smtp_password = smtp_config['smtp_password']
```

### Module Dependencies Pattern

#### Always Pass ConfigManager to Child Modules
```python
# ❌ WRONG
installer = PgVectorSetup(network_name=self.network_name)

# ✅ CORRECT
installer = PgVectorSetup(
    network_name=self.network_name,
    config_manager=self.config
)
```

### User Input Flow Pattern

#### 1. Section Box
```python
self._print_section_box("⚙️  CONFIGURAÇÃO SERVICE_NAME")
```

#### 2. Domain Suggestions
```python
suggested_domain = self.config.suggest_domain("service_name")
domain = self.get_user_input("Domínio", suggestion=suggested_domain)
```

#### 3. Credentials Generation
```python
# Auto-generate secure passwords
password = self.config.generate_secure_password(64)

# Get suggested email
email, _ = self.config.get_suggested_email_and_password("service_name")
```

#### 4. Visual Confirmation
```python
self._print_section_box("📋 CONFIRMAÇÃO DAS CONFIGURAÇÕES")
print(f"{self.VERDE}🌐{self.RESET} Domínio: {self.BRANCO}{domain}{self.RESET}")
print(f"{self.VERDE}📧{self.RESET} Email: {self.BRANCO}{email}{self.RESET}")
```

#### 5. Save to ConfigManager
```python
# Save config
self.config.save_app_config("service_name", {
    "domain": domain,
    "configured_at": datetime.now().isoformat()
})

# Save credentials
self.config.save_app_credentials("service_name", {
    "password": password,
    "email": email,
    "created_at": datetime.now().isoformat()
})
```

### Success Session Pattern (Post-Install)

#### Purpose
After successful installation, provide a UI for initial account configuration with smart suggestions.

#### Implementation Requirements
```python
def _show_success_session(self, domain: str):
    """Exibe sessão de sucesso para configurar conta inicial"""
    self._print_section_box("✅ SERVICE INSTALADO COM SUCESSO!")
    
    # Show access URL
    print(f"{self.VERDE}🌐 URL de Acesso: {self.BRANCO}https://{domain}{self.RESET}")
    
    # Generate and show suggested credentials
    suggested = self._generate_suggested_credentials()
    print(f"{self.BEGE}👤 DADOS SUGERIDOS PARA A CONTA:{self.RESET}")
    # Show suggestions...
    
    # Collect confirmed data
    final_credentials = self._collect_account_data(suggested)
    
    # Save to ConfigManager
    if final_credentials:
        self._save_account_credentials(final_credentials)
        self._show_final_summary(domain, final_credentials)
```

#### Key Features
1. **Smart Suggestions**: Auto-generate secure passwords and use existing user data
2. **Interactive Collection**: Allow user to confirm/modify suggestions
3. **ConfigManager Integration**: Save account credentials for future reference
4. **Visual Feedback**: Clear summary with access instructions

#### Services with Success Session
- ✅ **N8N**: Email, password, first/last name
- ✅ **Chatwoot**: Name, company, email, password
- 🔜 **Other services**: To be implemented as needed

## Refactoring Pattern Template

### Step 1: Add ConfigManager Import
```python
from utils.config_manager import ConfigManager
```

### Step 2: Update Constructor
```python
def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
    super().__init__("Service Name")
    self.config = config_manager or ConfigManager()
    self.network_name = network_name
    
    # Add color definitions
    self.LARANJA = "\033[38;5;173m"
    self.VERDE = "\033[32m"
    # ... all other colors ...

### Step 3: Replace File Operations
```python
# ❌ OLD - File write
os.makedirs("/root/dados_vps", exist_ok=True)
with open(f"/root/dados_vps/dados_{service}", 'w') as f:
    f.write(credentials)

# ✅ NEW - ConfigManager
credentials_data = {
    'username': 'user',
    'password': self.generated_password,
    'domain': self.domain,
    'created_at': datetime.now().isoformat()
}
self.config.save_app_credentials(service_name, credentials_data)
self.config.save_app_config(service_name, {
    'domain': self.domain,
    'configured_at': datetime.now().isoformat()
})
```

### Step 4: Replace File Reads
```python
# ❌ OLD - File read
with open("/root/dados_vps/dados_postgres", 'r') as f:
    for line in f:
        if "Password:" in line:
            password = line.split(":")[1].strip()

# ✅ NEW - ConfigManager
postgres_creds = self.config.get_app_credentials('postgres')
password = postgres_creds.get('password')
```

### Step 5: Update Domain Suggestions
```python
# ❌ OLD - Using hostname
hostname = socket.gethostname()
suggested = f"{service}.{hostname}"

# ✅ NEW - Using ConfigManager
suggested_domain = self.config.suggest_domain(service_name)
```

## Testing Migration

### Quick Verification Commands
```bash
# Count remaining dados_vps references (should decrease to 0)
grep -r "dados_vps" setup/ utils/ --exclude="*.md" | wc -l
# Current: 31 references in 10 files

# Verify ConfigManager adoption (should increase)
grep -r "ConfigManager" setup/ | wc -l  
# Current: 9 modules adopted

# Check specific module references
grep -n "dados_vps" setup/MODULE_setup.py
```

### Module-Specific Testing
```bash
# Test individual module after refactoring
sudo python3 -c "
from utils.config_manager import ConfigManager
from setup.MODULE_setup import MODULESetup
config = ConfigManager()
module = MODULESetup(config_manager=config)
module.run()
"

# Verify credentials were saved correctly
cat /root/livchat-config.json | jq '.credentials.MODULE_NAME'

# Check if old dados_vps file still exists (for backward compatibility)
ls -la /root/dados_vps/dados_MODULE_NAME
```

### Full Integration Test
```bash
# Run interactive menu to test all modules
sudo python3 main.py --verbose

# Monitor ConfigManager updates
tail -f /root/livchat-config.json | jq '.'
```

## Migration Priority & Strategy

### Order of Execution
1. **URGENT**: `pgvector_setup.py` (4 refs) - Blocks chatwoot/directus
2. **URGENT**: `directus_setup.py` (1 ref) - Depends on pgvector
3. **HIGH**: `evolution_setup.py` (2 refs) - Depends on postgres/redis
4. **HIGH**: Utils files - Core system functionality
5. **MEDIUM**: `grafana_setup.py` (3 refs) - Monitoring
6. **LOW**: `minio_setup.py` (4 refs) - Independent service
7. **LOW**: `gowa_setup.py` (3 refs) - WhatsApp service  
8. **COMPLEX**: `passbolt_setup.py` (10 refs) - Most references

### Common Migration Errors & Fixes

| Error | Cause | Solution |
|-------|-------|----------|
| `KeyError: 'password'` | Module reading old format | Check credential key names |
| `FileNotFoundError: dados_vps` | Old file dependency | Implement migration check |
| `NoneType has no attribute 'get'` | Missing config | Add null checks |
| `Domain suggests localhost` | Using hostname | Use `suggest_domain()` |

### Backward Compatibility Pattern
```python
def _get_postgres_password(self):
    """Get password with fallback to legacy file"""
    # Try ConfigManager first
    postgres_creds = self.config.get_app_credentials('postgres')
    if postgres_creds and postgres_creds.get('password'):
        return postgres_creds['password']
    
    # Fallback to legacy file for compatibility
    legacy_path = "/root/dados_vps/dados_postgres"
    if os.path.exists(legacy_path):
        with open(legacy_path, 'r') as f:
            for line in f:
                if "Password:" in line:
                    return line.split(":")[1].strip()
    
    raise ValueError("PostgreSQL password not found")
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Domain suggests `localhost` | Use `config.suggest_domain()` not hostname |
| Services not showing status | Check Docker daemon and Swarm mode |
| Menu spinner too slow | Ensure animation thread is running |
| Database migration errors | N8N auto-cleans old databases |

## Project Stats
- **34 setup modules** available
- **92-char menu width** standard
- **2-second** monitoring update interval
- **100ms** spinner animation rate
- **64-char** auto-generated passwords