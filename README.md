# LivChat Server Setup

Sistema modular de configuração de servidor Linux com Docker Swarm, Traefik, Portainer e aplicações via menu interativo.

## 🚀 Funcionalidades

### Infraestrutura Base
- [x] Configuração básica do sistema
- [x] Instalação e configuração do Docker
- [x] Inicialização do Docker Swarm
- [x] Deploy do Traefik com Let's Encrypt
- [x] Deploy do Portainer com suporte a agentes
- [x] Limpeza completa do ambiente Docker

### Bancos de Dados
- [x] Redis com persistência
- [x] PostgreSQL com PgVector
- [x] MinIO (S3 compatível)

### Aplicações
- [x] Chatwoot (Customer Support)
- [ ] N8N (Automação)
- [ ] Typebot (Chatbot Builder)
- [ ] Evolution API (WhatsApp)

## 🛠️ Pré-requisitos

- Linux (testado em Debian 12)
- Acesso root
- Conexão com a internet
- Domínio configurado (para SSL)

## 🚦 Como usar

### Instalação

```bash
# Clone o repositório
git clone https://github.com/pedrohnas0/SetupLivChat.git
cd SetupLivChat

# Execute o sistema (sempre inicia pelo menu)
sudo python3 main.py
```

### Menu Interativo

O sistema sempre inicia com um menu interativo que permite:

1. **Configuração Básica** - Hostname, timezone, pacotes essenciais
2. **Docker** - Instalação e configuração do Docker Swarm
3. **Traefik** - Proxy reverso com SSL automático
4. **Portainer** - Interface web para gerenciar containers
5. **Redis** - Cache e sessões
6. **PostgreSQL + PgVector** - Banco principal com suporte a vetores
7. **MinIO** - Armazenamento de arquivos
8. **Chatwoot** - Plataforma de atendimento ao cliente
9. **Limpeza** - Remove todos os containers e volumes

## 📁 Estrutura do Projeto

```
.
├── main.py                    # Ponto de entrada (sempre menu)
├── config.py                 # Configurações globais
├── requirements.txt          # Dependências Python
├── ARQUITETURA.md           # Documentação da arquitetura
├── setup/                   # Módulos de instalação
│   ├── basic_setup.py
│   ├── docker_setup.py
│   ├── traefik_setup.py
│   ├── portainer_setup.py
│   ├── redis_setup.py
│   ├── postgres_setup.py
│   ├── minio_setup.py
│   └── chatwoot_setup.py
├── templates/               # Templates Docker Compose
│   └── docker-compose/
└── utils/                   # Utilitários
    ├── interactive_menu.py      # Menu interativo
    ├── module_coordinator.py    # Coordenador de módulos
    ├── portainer_api.py         # API do Portainer
    └── template_engine.py       # Engine de templates
```

## 📊 Status do Projeto

- **Versão Atual**: 2.0
- **Última Atualização**: Janeiro 2025
- **Status**: Produção (Chatwoot funcional)

## 📝 Licença

MIT
