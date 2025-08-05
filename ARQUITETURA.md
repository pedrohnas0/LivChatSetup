# Arquitetura do Sistema de Setup

## Visão Geral
Sistema modular de setup inicial para servidores Linux, baseado no script original SetupOrionOriginal.sh, mas refatorado em Python com arquitetura modular e logging estruturado.

## Nova Estrutura de Arquivos (Organizada)

```
/root/CascadeProjects/
├── ARQUITETURA.md              # Este arquivo
├── main.py                     # Ponto de entrada principal
├── config.py                   # Configurações globais
├── setup/                      # Módulos de setup
│   ├── base_setup.py           # Classe base
│   ├── basic_setup.py          # Setup básico do sistema
│   ├── hostname_setup.py       # Configuração de hostname
│   ├── docker_setup.py         # Instalação do Docker
│   ├── traefik_setup.py        # Instalação do Traefik
│   └── portainer_setup.py      # Instalação do Portainer
├── templates/                  # Templates de configuração
│   ├── docker-compose/         # Stacks Docker Compose
│   │   ├── traefik.yaml.j2     # Template do Traefik
│   │   ├── portainer.yaml.j2   # Template do Portainer
│   │   └── network.yaml.j2     # Template de rede
│   └── configs/                # Arquivos de configuração
│       ├── traefik.toml.j2     # Config avançada do Traefik
│       └── nginx.conf.j2       # Templates Nginx (futuro)
├── utils/                      # Utilitários
│   ├── template_engine.py      # Engine para processar templates
│   ├── validators.py           # Validadores
│   └── helpers.py              # Funções auxiliares
└── logs/                       # Logs organizados
    ├── setup.log               # Log principal
    ├── docker.log              # Logs específicos do Docker
    └── traefik.log             # Logs específicos do Traefik
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

## Próximas Implementações

### Fase 1 (Concluída)
- [x] Basic Setup (setup_inicial.py)
- [x] Hostname Setup (hostname_setup.py) 
- [x] Docker Setup (docker_setup.py)
- [x] Logging estruturado (config.py)

### Fase 2 (Em desenvolvimento)
- [ ] Portainer Setup (portainer_setup.py)
- [ ] Traefik Setup (traefik_setup.py)
- [ ] Network Setup (firewall, portas)

### Fase 3 (Futuro)
- [ ] SSL/TLS Setup
- [ ] Aplicações específicas
- [ ] Monitoramento

### Fase 3 (Avançado)
- [ ] Aplicações específicas
- [ ] Monitoramento
- [ ] Backup automático

## Comandos de Uso

```bash
# Setup completo
sudo python3 main.py

# Setup específico
sudo python3 main.py --module hostname
sudo python3 main.py --module docker

# Modo debug
sudo python3 main.py --debug

# Configuração customizada
sudo python3 main.py --config custom_config.py
```

## Benefícios da Arquitetura

1. **Manutenibilidade**: Código modular e bem estruturado
2. **Extensibilidade**: Fácil adição de novos módulos
3. **Debugging**: Logs detalhados e estruturados
4. **Reutilização**: Componentes reutilizáveis
5. **Testabilidade**: Módulos independentes e testáveis
