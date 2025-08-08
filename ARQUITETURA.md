# Arquitetura do Sistema de Setup

## Visão Geral
Sistema modular de setup inicial para servidores Linux, baseado no script original SetupOrionOriginal.sh, mas refatorado em Python com arquitetura modular, menu interativo e deploy via API do Portainer.

**Versão Atual**: 2.0 - Janeiro 2025
**Status**: Produção (Chatwoot funcional)

## Nova Estrutura de Arquivos (Organizada)

```
/root/CascadeProjects/
├── ARQUITETURA.md              # Este arquivo
├── README.md                   # Documentação principal
├── main.py                     # Ponto de entrada (sempre menu)
├── config.py                   # Configurações globais
├── requirements.txt            # Dependências Python
├── setup/                      # Módulos de setup
│   ├── base_setup.py           # Classe base
│   ├── basic_setup.py          # Setup básico do sistema
│   ├── hostname_setup.py       # Configuração de hostname
│   ├── docker_setup.py         # Instalação do Docker
│   ├── traefik_setup.py        # Instalação do Traefik
│   ├── portainer_setup.py      # Instalação do Portainer
│   ├── redis_setup.py          # Redis com persistência
│   ├── postgres_setup.py       # PostgreSQL + PgVector
│   ├── minio_setup.py          # MinIO (S3 compatível)
│   ├── chatwoot_setup.py       # Chatwoot (Customer Support)
│   └── directus_setup.py       # Directus (Headless CMS)
├── templates/                  # Templates de configuração
│   └── docker-compose/         # Stacks Docker Compose
│       ├── traefik.yaml.j2     # Template do Traefik
│       ├── portainer.yaml.j2   # Template do Portainer
│       ├── redis.yaml.j2       # Template do Redis
│       ├── postgres.yaml.j2    # Template do PostgreSQL
│       ├── minio.yaml.j2       # Template do MinIO
│       ├── chatwoot.yaml.j2    # Template do Chatwoot
│       └── directus.yaml.j2    # Template do Directus
└── utils/                      # Utilitários
    ├── interactive_menu.py     # Menu interativo principal
    ├── module_coordinator.py   # Coordenador de módulos
    ├── portainer_api.py        # API do Portainer
    └── template_engine.py      # Engine para processar templates
```

**Benefícios da nova estrutura:**
- **Separação clara**: Módulos, templates e utilitários organizados
- **Templates externos**: Stacks Docker em arquivos .j2 (Jinja2)
- **Escalabilidade**: Fácil adição de novos módulos e templates
- **Manutenibilidade**: Cada componente tem seu lugar específico

## Módulos Implementados

### 1. Core (Núcleo)
- **main.py**: Coordenador principal que executa todos os módulos
- **config.py**: Configurações globais e sistema de logging estruturado
- **base_setup.py**: Classe abstrata base com funcionalidades comuns

### 2. Módulos de Setup (setup/)
- **base_setup.py**: Classe abstrata base com funcionalidades comuns
- **basic_setup.py**: Setup básico (update, timezone, pacotes) - IMPLEMENTADO
- **hostname_setup.py**: Configuração de hostname e /etc/hosts - IMPLEMENTADO
- **docker_setup.py**: Instalação do Docker e Docker Swarm - IMPLEMENTADO
- **traefik_setup.py**: Instalação do Traefik - IMPLEMENTADO
- **portainer_setup.py**: Instalação do Portainer - IMPLEMENTADO

### 3. Templates (templates/)
- **docker-compose/**: Stacks Docker Compose em Jinja2
- **configs/**: Arquivos de configuração de serviços
- **Vantagens**: Separação de lógica e configuração, reutilização, versionamento

### 4. Utilitários (utils/)
- **template_engine.py**: Processamento de templates Jinja2
- **validators.py**: Validação de entradas e pré-requisitos
- **helpers.py**: Funções auxiliares reutilizáveis

### 3. Regras de Logging Estabelecidas
- **NUNCA** usar separadores como '=================================================='
- **NUNCA** usar emojis nos logs (✓, ✗, etc.)
- Todas as informações devem estar na mesma linha
- Formato: `HH:MM:SS.mmm | LEVEL | message`
- Níveis centralizados em 8 caracteres
- Logs limpos e funcionais

## Padrões de Design

### 1. Logging Estruturado
- Formato: `HH:MM:SS.mmm | LEVEL | message`
- Níveis centralizados em 8 caracteres
- Cores no console, texto puro no arquivo
- Rotação de logs automática

### 2. Modularidade
- Cada módulo herda de `BaseSetup`
- Interface consistente: `run()`, `validate()`, `cleanup()`
- Dependências explícitas entre módulos

### 3. Tratamento de Erros
- Logs detalhados de comandos
- Timeout configurável
- Rollback em caso de falha

### 4. Configuração
- Arquivo de configuração centralizado
- Variáveis de ambiente
- Validação de configurações

## Fluxo de Execução

1. **Inicialização**
   - Carrega configurações
   - Configura logging
   - Valida privilégios

2. **Execução Sequencial**
   - Basic Setup (já implementado)
   - Hostname Setup
   - Docker Setup
   - Network Setup

3. **Finalização**
   - Relatório de status
   - Limpeza de recursos
   - Próximos passos

## Status das Implementações

### Infraestrutura Base (Concluída)
- [x] Basic Setup (basic_setup.py)
- [x] Hostname Setup (hostname_setup.py) 
- [x] Docker Setup (docker_setup.py)
- [x] Traefik Setup (traefik_setup.py)
- [x] Portainer Setup (portainer_setup.py)
- [x] Menu Interativo (interactive_menu.py)
- [x] Logging estruturado (config.py)

### Bancos de Dados (Concluída)
- [x] Redis Setup (redis_setup.py)
- [x] PostgreSQL + PgVector Setup (postgres_setup.py)
- [x] MinIO Setup (minio_setup.py)
- [x] Deploy via API do Portainer

### Aplicações (Em Produção)
- [x] Chatwoot Setup (chatwoot_setup.py) - **FUNCIONAL**
- [x] Directus Setup (directus_setup.py) - **FUNCIONAL**
- [ ] N8N Setup (n8n_setup.py)
- [ ] Typebot Setup (typebot_setup.py)
- [ ] Evolution API Setup (evolution_setup.py)

### Próximas Funcionalidades
- [ ] Backup automático
- [ ] Monitoramento (Grafana + Prometheus)
- [ ] Notificações (Discord/Telegram)
- [ ] Interface web para gerenciamento

## Como Usar

### Instalação e Execução

```bash
# Clone o repositório
git clone https://github.com/pedrohnas0/SetupLivChat.git
cd SetupLivChat

# Execute o sistema (sempre inicia pelo menu)
sudo python3 main.py
```

### Fluxo do Menu Interativo

1. **Menu Principal**: Escolha entre as opções disponíveis
2. **Coleta de Dados**: Sistema coleta informações necessárias
3. **Deploy**: Execução automática via API do Portainer
4. **Validação**: Verificação de serviços e logs
5. **Finalização**: Informações de acesso e próximos passos

## Benefícios da Arquitetura

1. **Manutenibilidade**: Código modular e bem estruturado
2. **Extensibilidade**: Fácil adição de novos módulos
3. **Debugging**: Logs detalhados e estruturados
4. **Reutilização**: Componentes reutilizáveis
5. **Testabilidade**: Módulos independentes e testáveis

## Notas de Correção e Diretrizes

- Reuso de banco para Directus
  - Diretriz: o Directus reutiliza o mesmo banco de dados do Chatwoot por padrão.
  - Template `templates/docker-compose/directus.yaml.j2` definido com `DB_DATABASE=chatwoot`.
  - O módulo `setup/directus_setup.py` garante a existência do DB `chatwoot` (não cria `directus`).
  - Benefício: simplifica a infraestrutura e reduz a sobrecarga operacional.

- Correção de método ausente em DirectusSetup
  - Erro: `'DirectusSetup' object has no attribute 'is_docker_running'`.
  - Ação: Implementado `is_docker_running()` em `setup/directus_setup.py`, espelhando a implementação de outros módulos (ex.: `TraefikSetup`).

- Persistência de credenciais do Directus
  - Agora também salvamos `admin_password` junto a `domain`, `admin_email`, `encryption_key` e `database` para referência operacional.

## Guia Técnico: Integração de uma Nova Stack

Este guia descreve, de forma técnica, como adicionar um novo serviço (stack) ao sistema.

- __Arquivos e locais impactados__
  - `templates/docker-compose/<servico>.yaml.j2` — Template Jinja2 do Docker Compose da stack.
  - `setup/<servico>_setup.py` — Módulo de setup que orquestra a instalação.
  - `utils/module_coordinator.py` — Registrar import e mapeamento do novo módulo.
  - `utils/interactive_menu.py` — Adicionar opção visual e executar o módulo.
  - Opcional: `utils/cloudflare_api.py` — Automação de DNS (se aplicável).

- __Fluxo do módulo `setup/<servico>_setup.py`__
  - Classe deve herdar de `BaseSetup` e implementar:
    - `validate_prerequisites()` — verificar Docker/Swarm, redes, bancos, etc.
    - `run()` — coletar inputs, preparar variáveis, tarefas pré-deploy (DNS/DB), chamar deploy, salvar credenciais.
  - Uso recomendado do `PortainerAPI().deploy_service_complete(...)`:
    - Parâmetros principais: `service_name`, `template_path`, `template_vars`, `volumes`, `wait_service`/`wait_services`, `credentials`.
  - Convenções:
    - Rede: `orion_network` (externa).
    - Labels Traefik com host por domínio e `traefik.docker.network={{ network_name }}`.
    - Definir `SECRET={{ encryption_key }}` quando o serviço requiser persistência de tokens.

- __Template Docker Compose (`templates/docker-compose/<servico>.yaml.j2`)__
  - Utilize `version: "3.8"`, `networks: { orion_network: { external: true } }`.
  - Services nomeados sob o stack; atenção aos nomes a usar em `wait_service`/`wait_services` (formato `stack_servico`).
  - Labels Traefik típicas:
    - `traefik.enable=true`
    - `traefik.http.routers.<servico>.rule=Host(`{{ '{{' }}` domain `{{ '}}' }}`)`
    - `traefik.http.routers.<servico>.entrypoints=websecure`
    - `traefik.http.routers.<servico>.tls.certresolver=letsencrypt`
    - `traefik.docker.network={{ '{{' }}` network_name `{{ '}}' }}`

- __Integração no `ModuleCoordinator`__ (`utils/module_coordinator.py`)
  - Import: `from setup.<servico>_setup import <Servico>Setup`
  - Mapeamento em `execute_module()`:
    - `elif module_name == '<servico>': return <Servico>Setup().run()`
  - Registro em `get_module_map()` para nome amigável e execução indireta.

- __Integração no `InteractiveMenu`__ (`utils/interactive_menu.py`)
  - Adicionar linha de exibição do menu (numeração consistente).
  - Em `execute_choice()`: bloco `elif choice == "NN": success = self.coordinator.execute_module('<servico>')`.

- __APIs e funções disponíveis__
  - `PortainerAPI` (`utils/portainer_api.py`):
    - Autenticação e alvo: `load_credentials`, `authenticate`, `get_endpoint_id`, `get_swarm_id`.
    - Deploy: `deploy_stack`, `check_stack_exists`.
    - Utilidades de orquestração: `create_volumes`, `wait_for_service`, `wait_for_multiple_services`, `verify_stack_running`.
    - Persistência e segredos: `save_service_credentials`, `generate_password`, `generate_hex_key`.
    - Alto nível: `deploy_service_complete(service_name, template_path, template_vars, volumes=None, wait_service=None, wait_services=None, credentials=None)`.
  - `TemplateEngine` (`utils/template_engine.py`): `render_template`, `render_to_file`, `list_templates`, `validate_template`.
  - `BaseSetup` (`setup/base_setup.py`): `validate_prerequisites` (abstrato), `run` (abstrato), `cleanup`, `check_root`, `run_command`, `check_package_installed`, `get_system_info`, `log_step_start`, `log_step_complete`.
  - Cloudflare (`utils/cloudflare_api.py`): `get_cloudflare_api(logger)` retornando client com `setup_dns_for_service(nome, [domains])`.

- __Checklist de entrega__
  - [ ] Template `.yaml.j2` parametrizado e validado (`TemplateEngine.validate_template`).
  - [ ] Módulo `<servico>_setup.py` com `run()` e `validate_prerequisites()` funcionando.
  - [ ] Volumes definidos em `deploy_service_complete` quando necessário.
  - [ ] `wait_service`/`wait_services` usando nomes reais dos serviços do stack.
  - [ ] Credenciais salvas em `/root/dados_vps/dados_<servico>` com chaves úteis.
  - [ ] Integrações no `ModuleCoordinator` e `InteractiveMenu` concluídas.
  - [ ] Acesso HTTPS validado via Traefik; DNS automatizado (se aplicável).
