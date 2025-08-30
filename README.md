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
- [x] Directus (Headless CMS)
- [ ] N8N (Automação)

## 🛠️ Pré-requisitos

- Linux (testado em Debian 12)
- Acesso root
- Conexão com a internet
- Domínio configurado (para SSL)

## 🚦 Como usar

### Execução rápida (one-liner)

```bash
# Padrão - sem logs no console
bash <(curl -sSL setup.livchat.ai)

# Com logs de erro
bash <(curl -sSL setup.livchat.ai) --quiet

# Com todos os logs (debug)
bash <(curl -sSL setup.livchat.ai) --verbose
```

### Instalação manual

```bash
# Clone o repositório
git clone https://github.com/pedrohnas0/LivChatSetup.git
cd LivChatSetup

# Execute o sistema (sempre inicia pelo menu)
sudo python3 main.py           # Padrão - sem logs no console
sudo python3 main.py --quiet   # Apenas ERROR e CRITICAL
sudo python3 main.py --verbose # Todos os logs (DEBUG)
```

### 📊 Controle de Logs

O sistema possui **3 modos de log**:

- **Padrão**: Console silencioso, logs salvos em arquivo
- **--quiet**: Console mostra apenas erros críticos
- **--verbose**: Console mostra debug completo

**Arquivo de log**: Sempre salva tudo em `/var/log/setup_inicial.log` (rotação 10MB, 5 backups)

### Menu Interativo

O sistema inicia com um menu interativo com as seguintes opções:

1. Configuração Básica do Sistema
2. Configuração de Hostname
3. Instalação do Docker + Swarm
4. Instalação do Traefik (Proxy Reverso)
5. Instalação do Portainer (Gerenciador Docker)

Banco de Dados:
6. Redis (Cache/Session Store)
7. PostgreSQL (Banco Relacional)
8. PostgreSQL + PgVector (Banco Vetorial)

Armazenamento:
9. MinIO (S3 Compatible Storage)

Aplicações:
10. Chatwoot (Customer Support Platform)
11. Directus (Headless CMS + Cloudflare DNS)
12. N8N (Workflow Automation + Cloudflare DNS)
13. Grafana (Stack de Monitoramento)
14. GOWA (WhatsApp API Multi Device)
15. LivChatBridge (Webhook Connector Chatwoot-GOWA)

Utilitários:
16. Instalar Tudo (Básico + Docker + Traefik + Portainer)
17. Limpeza Completa do Ambiente
18. (Removido) Rede Docker é configurada automaticamente e persistida
0. Sair

## 🧩 Notas de Correção e Operação

- Diretriz: Directus reutiliza o mesmo banco de dados do Chatwoot por padrão.
  - Template `templates/docker-compose/directus.yaml.j2` ajustado: `DB_DATABASE=chatwoot`.
  - O módulo `setup/directus_setup.py` garante a existência do DB `chatwoot` (não cria `directus`).
  - Motivo: simplificar a infra e reaproveitar o PostgreSQL já usado pelo Chatwoot.

- Correção de erro: `'DirectusSetup' object has no attribute 'is_docker_running'`.
  - Adicionado método `is_docker_running()` em `setup/directus_setup.py` seguindo o padrão dos outros módulos.
  - Causa: método não estava definido no `BaseSetup` e era esperado pelo fluxo de validação.

- Armazenamento de credenciais do Directus
  - Agora salvamos também `admin_password` juntamente com `domain`, `admin_email`, `encryption_key` e `database`.

## 🧭 Guia: Como adicionar uma nova stack

Siga este passo a passo para integrar uma nova aplicação ("stack") ao setup.

- __Arquivos a criar/alterar__
  - `templates/docker-compose/<servico>.yaml.j2` (novo template Docker Compose)
  - `setup/<servico>_setup.py` (novo módulo de setup)
  - `utils/module_coordinator.py` (import e mapeamento do módulo)
  - `utils/interactive_menu.py` (item no menu e execução)
  - Opcional: `utils/cloudflare_api.py` (se precisar automatizar DNS)

- __Padrão do módulo `setup/<servico>_setup.py`__
  - Herde de `BaseSetup` e implemente:
    - `validate_prerequisites()` para checagens (ex.: Docker, DB, rede).
    - `run()` como fluxo principal: coletar inputs, preparar variáveis, pré-tarefas (DNS/DB), chamar deploy e salvar credenciais.
  - Utilize `PortainerAPI().deploy_service_complete(...)` com:
    - `service_name`: nome da stack (ex.: `gowa`).
    - `template_path`: caminho relativo Jinja2 (ex.: `docker-compose/gowa.yaml.j2`).
    - `template_vars`: dicionário de variáveis usadas no template.
    - `volumes=[...]`: lista de volumes a criar antes do deploy (se houver).
    - `wait_service` ou `wait_services=[...]`: nomes exatos dos serviços (formato `stack_servico`).
    - `credentials={...}`: pares a salvar em `/root/dados_vps/dados_<servico>`.
  - Dicas úteis:
    - Gere segredos com `PortainerAPI.generate_hex_key()`/`generate_password()`.
    - Se o serviço exigir sessão persistente, defina `SECRET={{ encryption_key }}` no template.
    - Para DNS, use `get_cloudflare_api(logger)` e `setup_dns_for_service("Nome", [domain])`.

- __Template Docker Compose `templates/docker-compose/<servico>.yaml.j2`__
  - Use uma rede externa referenciada por `{{ network_name }}` (sem valor hardcoded).
  - Inclua labels do Traefik:
    - `traefik.http.routers.<servico>.rule=Host(`{{ '{{' }}` domain `{{ '}}' }}`)`
    - `traefik.http.routers.<servico>.tls.certresolver=letsencrypt`
    - `traefik.docker.network={{ '{{' }}` network_name `{{ '}}' }}`
  - Parametrize variáveis como `domain`, `network_name`, emails/senhas e chaves (`encryption_key`).

- __Integração no `ModuleCoordinator`__
  - `from setup.<servico>_setup import <Servico>Setup`
  - Em `execute_module()`: `elif module_name == '<servico>': return <Servico>Setup().run()`
  - Em `get_module_map()`: inclua a entrada com rótulo amigável.

- __Integração no `InteractiveMenu`__
  - Adicione a linha visual do menu e o bloco correspondente em `execute_choice()`:
    - `elif choice == "NN": success = self.coordinator.execute_module('<servico>')`
  - Ajuste a numeração exibida mantendo o padrão.

- __APIs e utilitários disponíveis__
  - `PortainerAPI` principais:
    - `deploy_service_complete(service_name, template_path, template_vars, volumes=None, wait_service=None, wait_services=None, credentials=None)`
    - `create_volumes`, `deploy_stack`, `wait_for_service`, `wait_for_multiple_services`, `verify_stack_running`, `save_service_credentials`, `generate_password`, `generate_hex_key`.
  - `TemplateEngine`: `render_template`, `render_to_file`, `list_templates`.
  - `BaseSetup`: `run_command`, `check_root`, helpers genéricos.
  - `Cloudflare API`: `get_cloudflare_api()` com `setup_dns_for_service(nome, [domains])`.

- __Checklist rápido__
  - [ ] Template `.yaml.j2` criado e validado.
  - [ ] Módulo `<servico>_setup.py` implementado (`run()` funcional).
  - [ ] Import e mapeamento no `ModuleCoordinator` concluídos.
  - [ ] Opção adicionada no `InteractiveMenu` (impressão + execução).
  - [ ] Labels do Traefik e rede externa referenciada via `{{ network_name }}` corretas.
  - [ ] `SECRET`/`KEY` definidos quando aplicável.
  - [ ] `wait_service(s)` configurado conforme os nomes reais dos serviços.
  - [ ] Credenciais persistidas em `/root/dados_vps/dados_<servico>`.
  - [ ] Testado: `docker service ls` e acesso HTTPS.

## 📁 Estrutura do Projeto

```
.
├── main.py                      # Ponto de entrada (menu)
├── config.py                    # Configurações / logging
├── requirements.txt             # Dependências Python
├── ARQUITETURA.md               # Documentação de arquitetura
├── setup/                       # Módulos de instalação
│   ├── base_setup.py
│   ├── basic_setup.py
│   ├── hostname_setup.py
│   ├── docker_setup.py
│   ├── traefik_setup.py
│   ├── portainer_setup.py
│   ├── cleanup_setup.py
│   ├── redis_setup.py
│   ├── postgres_setup.py
│   ├── pgvector_setup.py
│   ├── minio_setup.py
│   ├── chatwoot_setup.py
│   ├── directus_setup.py
│   ├── n8n_setup.py
│   ├── grafana_setup.py
│   ├── gowa_setup.py
│   └── livchatbridge_setup.py
├── templates/                   # Templates Docker Compose (Jinja2)
│   └── docker-compose/
│       ├── traefik.yaml.j2
│       ├── portainer.yaml.j2
│       ├── redis.yaml.j2
│       ├── postgres.yaml.j2
│       ├── pgvector.yaml.j2
│       ├── minio.yaml.j2
│       ├── chatwoot.yaml.j2
│       ├── directus.yaml.j2
│       ├── grafana.yaml.j2
│       ├── gowa.yaml.j2
│       └── livchatbridge.yaml.j2
└── utils/                       # Utilitários
    ├── interactive_menu.py      # Menu interativo
    ├── module_coordinator.py    # Coordenador de módulos
    ├── portainer_api.py         # Integração Portainer
    └── template_engine.py       # Engine de templates
```

## 📝 Licença

MIT
