# LivChat Server Setup

Sistema modular de configuração de servidor Linux com Docker Swarm, Traefik e Portainer.

## 🚀 Funcionalidades

- [x] Configuração básica do sistema
- [x] Instalação e configuração do Docker
- [x] Inicialização do Docker Swarm
- [x] Deploy do Traefik com Let's Encrypt
- [x] Deploy do Portainer com suporte a agentes
- [x] Limpeza completa do ambiente Docker

## 🛠️ Pré-requisitos

- Linux (testado em Debian 12)
- Acesso root
- Conexão com a internet

## 🚦 Como usar

```bash
# Instalar dependências
apt-get update && apt-get install -y python3 python3-pip
pip3 install -r requirements.txt

# Executar setup básico
python3 main.py --hostname seu-servidor --email seu@email.com

# Executar módulos específicos
python3 main.py --hostname seu-servidor --module basic,docker,traefik,portainer

# Limpar ambiente (cuidado!)
python3 main.py --module cleanup
```

## 📁 Estrutura do Projeto

```
.
├── main.py               # Ponto de entrada
├── config.py            # Configurações globais
├── requirements.txt     # Dependências Python
├── setup/               # Módulos de instalação
├── templates/           # Templates Docker Compose
└── utils/               # Utilitários
```

## 📝 Licença

MIT
