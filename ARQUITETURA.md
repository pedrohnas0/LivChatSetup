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
│   └── chatwoot_setup.py       # Chatwoot (Customer Support)
├── templates/                  # Templates de configuração
│   └── docker-compose/         # Stacks Docker Compose
│       ├── traefik.yaml.j2     # Template do Traefik
│       ├── portainer.yaml.j2   # Template do Portainer
│       ├── redis.yaml.j2       # Template do Redis
│       ├── postgres.yaml.j2    # Template do PostgreSQL
│       ├── minio.yaml.j2       # Template do MinIO
│       └── chatwoot.yaml.j2    # Template do Chatwoot
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
