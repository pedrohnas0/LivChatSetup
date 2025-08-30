# 🚀 LivChat Setup

**Sistema modular para deploy automatizado de aplicações Docker com interface interativa**

*Baseado no projeto [SetupOrion](https://github.com/oriondesign2015/SetupOrion) do Willian - Orion Design*

---

## ⚡ **Instalação**

```bash
# Execução com um comando
bash <(curl -sSL setup.livchat.ai)

# Com logs de debug  
bash <(curl -sSL setup.livchat.ai) --verbose

# Instalação manual
git clone https://github.com/pedrohnas0/LivChatSetup.git
cd LivChatSetup && sudo python3 main.py
```

## 🎯 **Funcionalidades**

- **Menu TUI interativo** com seleção múltipla e pesquisa
- **SSL automático** com Let's Encrypt  
- **DNS automático** via Cloudflare API
- **Configuração persistente** em JSON
- **34 aplicações** prontas para produção
- **Deploy via Docker Swarm** com Portainer

## 📦 **Aplicações Disponíveis**

### Infraestrutura Base
- Configuração do sistema (email, hostname, DNS, rede, timezone)  
- Docker + Swarm
- Traefik (proxy reverso + SSL)
- Portainer (gerenciador Docker)

### Bancos de Dados  
- PostgreSQL + PgVector
- Redis  
- MinIO (S3 compatível)

### Aplicações
- **Chatwoot** - Customer support platform
- **Directus** - Headless CMS
- **N8N** - Automação de workflows  
- **Grafana** - Monitoramento
- **Evolution API** - WhatsApp API
- **GOWA** - WhatsApp Multi Device
- **LivChatBridge** - Webhook connector

### Utilitários
- Limpeza completa do ambiente
- Geração de credenciais seguras
- Backup automático de configurações

## 🔧 **Requisitos**

- Linux (testado Debian 12, Ubuntu 20+)
- Acesso root
- Internet ativa  
- Domínio configurado (opcional)

---

### 💝 Agradecimentos

**Willian - [Orion Design](https://oriondesign.art.br/)**

Projeto original: [SetupOrion](https://github.com/oriondesign2015/SetupOrion)