<div align="center">

# 🚀 LivChat Setup

### **Sistema automatizado de deploy de aplicações com Docker Swarm**
*Configure seu servidor Linux em minutos com interface interativa e DNS automático*

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

</div>

---

## 📋 **O que é o LivChat Setup?**

Um **sistema modular e inteligente** que automatiza a configuração completa de servidores Linux para **produção**. Com uma **interface interativa TUI**, deploy via **Docker Swarm**, **SSL automático** com Let's Encrypt e **DNS automático** via Cloudflare.

### ✨ **Por que escolher o LivChat Setup?**

- 🎯 **Menu interativo** com seleção múltipla e pesquisa
- 🔒 **SSL automático** com Let's Encrypt (zero configuração)
- 🌐 **DNS automático** via Cloudflare API
- 📦 **34 aplicações** prontas para produção
- 🔄 **Configuração persistente** (execute quantas vezes quiser)
- 🚀 **Deploy com um comando** - `bash <(curl -sSL setup.livchat.ai)`

---

## ⚡ **Instalação Rápida**

```bash
# 🚀 Execução com um comando (recomendado)
bash <(curl -sSL setup.livchat.ai)

# 📝 Com logs de debug
bash <(curl -sSL setup.livchat.ai) --verbose

# 🔇 Apenas erros críticos
bash <(curl -sSL setup.livchat.ai) --quiet
```

### 🛠️ **Instalação Manual**

```bash
git clone https://github.com/pedrohnas0/LivChatSetup.git
cd LivChatSetup
sudo python3 main.py
```

---

## 🎯 **Aplicações Disponíveis**

<div align="center">

### 🏗️ **Infraestrutura**
**Docker** • **Traefik** • **Portainer** • **Configuração Base**

### 🗄️ **Bancos de Dados**
**PostgreSQL + PgVector** • **Redis** • **MinIO (S3)**

### 💬 **Aplicações**
**Chatwoot** • **Directus** • **N8N** • **Grafana** • **Evolution API**

### 🔧 **Utilitários**
**DNS Automático** • **SSL Automático** • **Limpeza Completa**

</div>

---

## 🎮 **Interface do Sistema**

```
╭─ SETUP LIVCHAT ─────────────────────── Selecionados: 3/34 ─╮
│ ↑/↓ navegar · → marcar (●/○) · Enter executar · Digite para pesquisar         │
│                                                               │
│ → ● [1] Config (E-mail, Hostname, Cloudflare, Rede, Timezone)│
│   ○ [2] Instalação do Docker + Swarm                         │  
│   ○ [3] Instalação do Traefik (Proxy Reverso)               │
│   ● [4] Chatwoot (Customer Support Platform)                │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

**Recursos da Interface:**
- 🔍 **Pesquisa em tempo real** - digite para filtrar
- 🎯 **Seleção múltipla** - marque quantas aplicações quiser  
- 📱 **Menu responsivo** - adapta-se ao terminal
- 🔄 **Pós-instalação** - instale mais apps ou finalize

---

## 🌟 **Recursos Premium**

### 🌐 **DNS Automático Cloudflare**
- Detecção automática de zonas
- Menu interativo de seleção
- Subdomínios personalizáveis
- Registros A automáticos

### 🔒 **SSL Automático**
- Let's Encrypt integrado
- Renovação automática
- Configuração zero

### 📊 **Monitoramento Inteligente**  
- Logs estruturados com rotação
- Verificação de saúde dos serviços
- Credenciais seguras salvas

---

## 🔧 **Pré-requisitos**

- 🐧 **Linux** (testado em Debian 12, Ubuntu 20+)
- 👑 **Acesso root**
- 🌐 **Internet** ativa
- 🔗 **Domínio** configurado (opcional para DNS automático)

---

## 📚 **Documentação**

📖 **[CLAUDE.md](./CLAUDE.md)** - Guia completo para desenvolvedores

🏗️ **[Como adicionar novas aplicações](./CLAUDE.md#adding-new-services)** - Tutorial passo-a-passo

---

## 💝 **Agradecimentos Especiais**

<div align="center">

### 🎨 **Willian - Orion Design**

*Agradecimento especial ao* **Willian da [Orion Design](https://oriondesign.art.br/)** *pelo projeto original que serviu de base para este sistema.*

🔗 **Repositório Original:** [SetupOrion](https://github.com/oriondesign2015/SetupOrion)  
🌐 **Site Oficial:** [oriondesign.art.br](https://oriondesign.art.br/)

*Este projeto é uma evolução e modernização do SetupOrion original, com interface TUI, configuração persistente e recursos avançados de automação.*

</div>

---

## 📞 **Suporte**

💬 **Issues:** [GitHub Issues](https://github.com/pedrohnas0/LivChatSetup/issues)

📧 **Contato:** [Criar Issue](https://github.com/pedrohnas0/LivChatSetup/issues/new)

---

## 📄 **Licença**

Este projeto está licenciado sob a **Licença MIT** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">

**⭐ Se este projeto te ajudou, considere dar uma estrela!**

*Feito com 💜 pela comunidade*

</div>