#!/usr/bin/env python3

import subprocess
import logging
import os
from datetime import datetime
from .base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from setup.pgvector_setup import PgVectorSetup
from utils.cloudflare_api import get_cloudflare_api
from utils.config_manager import ConfigManager

class ChatwootSetup(BaseSetup):
    """Setup do Chatwoot com integração ConfigManager e padrão visual N8N"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do Chatwoot")
        self.portainer = PortainerAPI()
        self.network_name = network_name
        self.config = config_manager or ConfigManager()

    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
        
        # Garante PgVector (instala automaticamente se necessário)
        if not self.ensure_pgvector():
            return False
            
        return True

    def _is_pgvector_running(self) -> bool:
        """Verifica se PgVector está rodando"""
        try:
            result = subprocess.run(
                "docker service ls --filter name=pgvector --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return "pgvector" in result.stdout
        except Exception:
            return False

    def is_docker_running(self) -> bool:
        """Verifica se Docker está rodando"""
        try:
            result = subprocess.run(
                "docker info",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.debug(f"Erro ao verificar Docker: {e}")
            return False

    def ensure_pgvector(self) -> bool:
        """Garante que PgVector esteja instalado e rodando; instala se necessário."""
        if self._is_pgvector_running():
            return True
        self.logger.warning("PgVector não encontrado/rodando. Iniciando instalação automática...")
        try:
            installer = PgVectorSetup(network_name=self.network_name, config_manager=self.config)
            if not installer.run():
                self.logger.error("Falha ao instalar/configurar PgVector")
                return False
            # Revalida
            if self._is_pgvector_running():
                return True
            self.logger.error("PgVector ainda não está rodando após instalação")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao garantir PgVector: {e}")
            return False

    def _get_pgvector_password(self) -> str:
        """Obtém senha do PgVector via ConfigManager"""
        try:
            # Obtém do ConfigManager
            pgvector_creds = self.config.get_app_credentials("pgvector")
            if pgvector_creds and pgvector_creds.get("password"):
                return pgvector_creds["password"]
            
            # Se não encontrou, tenta o fallback do arquivo legado (temporário)
            # TODO: Remover após garantir que PgVector sempre salva no ConfigManager
            try:
                with open("/root/dados_vps/dados_pgvector", 'r') as f:
                    for line in f:
                        if line.startswith("Senha:"):
                            password = line.split(":", 1)[1].strip()
                            self.logger.warning("Usando senha do arquivo legado. PgVector deve ser reinstalado para usar ConfigManager.")
                            return password
            except FileNotFoundError:
                pass
            
            # Se não encontrou em nenhum lugar, erro fatal
            raise ValueError("PgVector credentials not found in ConfigManager or legacy file")
            
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do PgVector: {e}")
            raise
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal de forma segura"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback
    
    def _print_section_box(self, title: str, width: int = None):
        """Cria box de seção menor seguindo padrão do projeto"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(60, terminal_width - 10)
        
        # Remove códigos de cor para calcular tamanho real
        import re
        clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
        
        line = "─" * (width - 1)
        print(f"\n{self.CINZA}╭{line}╮{self.RESET}")
        
        # Centralização padrão
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
        
        # Adicionar 2 espaços extras para mover borda direita
        extra_spaces = "  "
        
        print(f"{self.CINZA}│{colored_line}{extra_spaces}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None) -> str:
        """Coleta entrada do usuário com sugestão opcional seguindo padrão do projeto"""
        try:
            if suggestion:
                full_prompt = f"{prompt} (Enter para '{suggestion}' ou digite outro)"
            else:
                full_prompt = prompt
                
            value = input(f"{full_prompt}: ").strip()
            
            # Se não digitou nada e há sugestão, usa a sugestão
            if not value and suggestion:
                return suggestion
                
            if required and not value:
                self.logger.warning("Valor obrigatório não fornecido")
                return None
                
            return value if value else None
            
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return None

    def collect_user_inputs(self) -> dict:
        """Coleta informações do usuário seguindo padrão visual do N8N"""
        self._print_section_box("💬 CONFIGURAÇÃO CHATWOOT")
        
        # Domínio com sugestão inteligente
        suggested_domain = self.config.suggest_domain("chatwoot")
        while True:
            domain = self.get_user_input("Domínio do Chatwoot", suggestion=suggested_domain)
            if domain and '.' in domain:
                break
            print(f"{self.VERMELHO}❌ Domínio é obrigatório e deve ser válido!{self.RESET}")
        
        # Verifica configuração SMTP (padrão N8N)
        smtp_config = self.config.get_app_config("smtp")
        if not smtp_config or not smtp_config.get("configured", False):
            self._print_section_box("⚠️  SMTP NÃO CONFIGURADO")
            print(f"{self.VERMELHO}❌ Chatwoot precisa de configuração SMTP para envio de emails!{self.RESET}")
            print(f"{self.BEGE}Configure o SMTP primeiro no menu principal (item 2).{self.RESET}")
            print()
            
            configure_now = self.get_user_input("Deseja configurar SMTP agora", suggestion="sim")
            if configure_now and configure_now.lower() in ['sim', 's', 'yes', 'y']:
                from setup.smtp_setup import SMTPSetup
                smtp_setup = SMTPSetup(config_manager=self.config)
                if not smtp_setup.run():
                    print(f"{self.VERMELHO}❌ Falha na configuração SMTP. Chatwoot não pode prosseguir.{self.RESET}")
                    return None
                # Recarrega configuração após setup
                smtp_config = self.config.get_app_config("smtp")
            else:
                print(f"{self.VERMELHO}❌ Chatwoot cancelado. Configure SMTP primeiro.{self.RESET}")
                return None
        
        self._print_section_box("✅ SMTP CONFIGURADO")
        print(f"{self.VERDE}📧{self.RESET} Servidor: {smtp_config['smtp_host']}:{smtp_config['smtp_port']}")
        print(f"{self.VERDE}📨{self.RESET} Remetente: {smtp_config['sender_email']}")
        print()
        
        # Converte configurações para formato do Chatwoot
        smtp_email = smtp_config['sender_email']
        smtp_user = smtp_config['smtp_username']
        smtp_password = smtp_config['smtp_password']
        smtp_host = smtp_config['smtp_host']
        smtp_port = str(smtp_config['smtp_port'])
        smtp_ssl = smtp_config['smtp_ssl']
        smtp_domain = smtp_config.get('smtp_domain', smtp_email.split("@")[1] if "@" in smtp_email else "")
        
        # Nome da empresa (usa hostname como padrão)
        try:
            result = subprocess.run("hostname", shell=True, capture_output=True, text=True)
            company_name = result.stdout.strip() if result.returncode == 0 else "Chatwoot"
        except:
            company_name = "Chatwoot"
        
        # Confirmação visual melhorada (padrão N8N)
        self._print_section_box("📋 CONFIRMAÇÃO DAS CONFIGURAÇÕES")
        print(f"{self.VERDE}🌐{self.RESET} Domínio: {self.BRANCO}{domain}{self.RESET}")
        print(f"{self.VERDE}🏢{self.RESET} Empresa: {self.BRANCO}{company_name}{self.RESET}")
        print()
        print(f"{self.BEGE}📧 SMTP (obtido da configuração centralizada):{self.RESET}")
        print(f"{self.VERDE}  📨{self.RESET} Servidor: {self.BRANCO}{smtp_host}:{smtp_port}{self.RESET}")
        print(f"{self.VERDE}  📧{self.RESET} Remetente: {self.BRANCO}{smtp_email}{self.RESET}")
        ssl_method = "SSL/TLS" if smtp_ssl == "true" else "STARTTLS"
        print(f"{self.VERDE}  🔒{self.RESET} Segurança: {self.BRANCO}{ssl_method}{self.RESET}")
        
        # Avisar sobre DNS automático
        if self.config.is_cloudflare_auto_dns_enabled():
            print(f"\n{self.VERDE}✅{self.RESET} DNS será configurado automaticamente via Cloudflare")
        else:
            print(f"\n{self.BEGE}⚠️{self.RESET}  Você precisará configurar o DNS manualmente")
        
        print()
        print(f"{self.BEGE}Pressione {self.VERDE}Enter{self.BEGE} para confirmar · {self.VERMELHO}N{self.BEGE} para cancelar{self.RESET}")
        
        confirm = input("Confirmar? (Enter=Sim, N=Não): ").strip()
        if confirm and confirm.lower() in ['n', 'não', 'nao', 'no']:
            self.logger.info("Instalação cancelada pelo usuário")
            return None
        
        # Gerar secrets usando ConfigManager
        encryption_key = self.config.generate_secure_password(32)  # 32 chars para encryption key
        pgvector_password = self._get_pgvector_password()
        
        config_data = {
            'domain': domain,
            'company_name': company_name,
            'encryption_key': encryption_key,
            'smtp_email': smtp_email,
            'smtp_domain': smtp_domain,
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_ssl': smtp_ssl,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'pgvector_password': pgvector_password,
            'network_name': self.network_name
        }
        
        # Salva configuração no ConfigManager
        self.config.save_app_config("chatwoot", {
            "domain": domain,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "company_name": company_name
        })
        
        # Salva credenciais no ConfigManager
        self.config.save_app_credentials("chatwoot", {
            "smtp_email": smtp_email,
            "smtp_user": smtp_user,
            "smtp_password": smtp_password,
            "encryption_key": encryption_key
        })
        
        return config_data

    def create_database(self) -> bool:
        """Cria banco de dados no PgVector"""
        try:
            create_db_cmd = """
            docker exec -i $(docker ps -q -f name=pgvector) psql -U postgres -c "CREATE DATABASE chatwoot;"
            """
            
            result = subprocess.run(
                create_db_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 or "already exists" in result.stderr:
                self.logger.info("Banco de dados chatwoot criado/verificado")
                return True
            else:
                self.logger.warning(f"Aviso ao criar banco: {result.stderr}")
                return True  # Continua mesmo com avisos
                
        except Exception as e:
            self.logger.error(f"Erro ao criar banco de dados: {e}")
            return False

    def setup_dns_records(self, domain: str) -> bool:
        """Configura registros DNS via Cloudflare integrado ao ConfigManager"""
        if not self.config.is_cloudflare_auto_dns_enabled():
            self.logger.info("DNS automático não configurado, pulando...")
            return True
            
        self.logger.info("🌐 Configurando registros DNS via Cloudflare...")
        cf = get_cloudflare_api(logger=self.logger, config_manager=self.config)
        if not cf:
            self.logger.error("❌ Falha ao inicializar Cloudflare API")
            return False
            
        # Usa novo método integrado
        return cf.create_app_dns_record("chatwoot", domain)

    def run(self):
        """Executa instalação do Chatwoot usando métodos genéricos do PortainerAPI"""
        try:
            self.logger.info("Iniciando instalação do Chatwoot")
            
            # Loop para coleta e confirmação de dados
            variables = None
            while not variables:
                variables = self.collect_user_inputs()
                if not variables:
                    print("\nVamos tentar novamente...\n")
            
            # DNS via Cloudflare (não bloqueante)
            if not self.setup_dns_records(variables['domain']):
                self.logger.warning("Falha na configuração DNS, continuando mesmo assim...")
            
            # Criar banco de dados
            if not self.create_database():
                self.logger.error("Falha ao criar banco de dados")
                return False
            
            # Deploy completo usando método genérico do PortainerAPI
            success = self.portainer.deploy_service_complete(
                service_name="chatwoot",
                template_path="docker-compose/chatwoot.yaml.j2",
                template_vars=variables,
                volumes=[
                    "chatwoot_storage",
                    "chatwoot_public", 
                    "chatwoot_mailer",
                    "chatwoot_mailers",
                    "chatwoot_redis"
                ],
                wait_services=["chatwoot_chatwoot_redis", "chatwoot_chatwoot_app", "chatwoot_chatwoot_sidekiq"],
                credentials={
                    'domain': variables['domain'],
                    'company_name': variables['company_name'],
                    'encryption_key': variables['encryption_key'],
                    'smtp_email': variables['smtp_email'],
                    'smtp_user': variables['smtp_user'],
                    'smtp_password': variables['smtp_password'],
                    'smtp_host': variables['smtp_host'],
                    'smtp_port': variables['smtp_port']
                }
            )
            
            if success:
                # Executa migrações do banco de dados
                if self.run_database_migrations():
                    self.logger.info("Instalação do Chatwoot concluída com sucesso")
                    self.logger.info(f"Acesse: https://{variables['domain']}")
                    self.logger.info(f"Chave de criptografia: {variables['encryption_key']}")
                    
                    # Sessão de sucesso para configurar conta inicial
                    self._show_success_session(variables['domain'])
                    
                    return True
                else:
                    self.logger.error("Falha nas migrações do banco de dados")
                    return False
            else:
                self.logger.error("Falha na instalação do Chatwoot")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro durante instalação do Chatwoot: {e}")
            return False
    
    def _show_success_session(self, domain: str):
        """Exibe sessão de sucesso para configurar conta inicial do Chatwoot"""
        self._print_section_box("✅ CHATWOOT INSTALADO COM SUCESSO!")
        
        print(f"{self.VERDE}🌐 URL de Acesso: {self.BRANCO}https://{domain}{self.RESET}")
        print()
        print(f"{self.BEGE}📝 PRÓXIMO PASSO: Configure sua conta de administrador no Chatwoot{self.RESET}")
        print()
        
        # Gera credenciais sugeridas usando ConfigManager
        suggested_credentials = self._generate_suggested_credentials()
        
        print(f"{self.BEGE}👤 DADOS SUGERIDOS PARA A CONTA:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Nome: {self.BRANCO}{suggested_credentials['name']}{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Empresa: {self.BRANCO}{suggested_credentials['company']}{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Email: {self.BRANCO}{suggested_credentials['email']}{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Senha: {self.BRANCO}{suggested_credentials['password']}{self.RESET}")
        
        print()
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para continuar...{self.RESET}")
        
        # Coleta credenciais confirmadas pelo usuário
        final_credentials = self._collect_chatwoot_account_data(suggested_credentials)
        
        if final_credentials:
            self._save_chatwoot_account_credentials(final_credentials)
            self._show_final_summary(domain, final_credentials)
    
    def _generate_suggested_credentials(self) -> dict:
        """Gera credenciais sugeridas para conta do Chatwoot"""
        email = self.config.get_user_email() or "admin@livchat.ai"
        password = self.config.generate_secure_password(64)  # 64 caracteres seguros com caracteres especiais
        
        # Obtém dados do usuário do config global
        user_data = self.config.config_data["global"]
        
        # Nome completo (junta primeiro e último se existirem)
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        else:
            full_name = "Administrador"
        
        # Nome da empresa - só retorna se foi explicitamente configurado
        company_name = user_data.get("company_name", "")
        
        return {
            "name": full_name,
            "company": company_name,  # Pode ser vazio se não foi configurado
            "email": email,
            "password": password
        }
    
    def _collect_chatwoot_account_data(self, suggested_credentials: dict) -> dict:
        """Coleta dados da conta do Chatwoot com sugestões"""
        self._print_section_box("👤 CONFIGURE SUA CONTA CHATWOOT")
        
        print(f"{self.BEGE}Confirme os dados para sua conta de administrador no Chatwoot:{self.RESET}")
        print(f"{self.BEGE}(Enter para aceitar sugestão ou digite outro valor){self.RESET}")
        print()
        
        # Nome
        name = self.get_user_input(
            "Nome completo",
            suggestion=suggested_credentials['name']
        )
        if not name:
            name = suggested_credentials['name']
        
        # Empresa - só pergunta se já foi configurado antes
        if suggested_credentials['company']:
            company = self.get_user_input(
                "Nome da empresa",
                suggestion=suggested_credentials['company']
            )
            if not company:
                company = suggested_credentials['company']
        else:
            # Se não tem sugestão, pergunta sem sugestão
            company = self.get_user_input("Nome da empresa")
            if not company:
                company = "Chatwoot"  # Valor padrão se não informar
        
        # Email
        email = self.get_user_input(
            "Email de trabalho",
            suggestion=suggested_credentials['email']
        )
        if not email:
            email = suggested_credentials['email']
        
        # Senha
        print(f"\n{self.BEGE}⚠️  Senha sugerida (64 caracteres seguros com caracteres especiais):{self.RESET}")
        print(f"    {self.BRANCO}{suggested_credentials['password']}{self.RESET}")
        password = self.get_user_input(
            "Senha (Enter para usar sugerida)",
            suggestion="****"
        )
        if not password or password == "****":
            password = suggested_credentials['password']
        
        return {
            "name": name,
            "company": company,
            "email": email,
            "password": password
        }
    
    def _save_chatwoot_account_credentials(self, credentials: dict):
        """Salva credenciais da conta do Chatwoot"""
        # Atualiza credenciais do Chatwoot com dados da conta
        existing_creds = self.config.get_app_credentials('chatwoot')
        existing_creds.update({
            'account_name': credentials['name'],
            'account_company': credentials['company'],
            'account_email': credentials['email'],
            'account_password': credentials['password'],
            'account_created_at': datetime.now().isoformat()
        })
        self.config.save_app_credentials('chatwoot', existing_creds)
        
        # Salva nome da empresa no config global se não existir
        if credentials['company'] and credentials['company'] != "Chatwoot":
            user_data = self.config.config_data["global"]
            if not user_data.get("company_name"):
                user_data["company_name"] = credentials['company']
                self.config.save_config()
        
        self.logger.info("Credenciais da conta Chatwoot salvas no ConfigManager")
    
    def _show_final_summary(self, domain: str, credentials: dict):
        """Exibe resumo final com credenciais salvas"""
        self._print_section_box("📋 RESUMO DA INSTALAÇÃO")
        
        print(f"{self.VERDE}✅ Chatwoot instalado e configurado com sucesso!{self.RESET}")
        print()
        print(f"{self.BEGE}📌 INFORMAÇÕES DE ACESSO:{self.RESET}")
        print(f"   {self.VERDE}🌐{self.RESET} URL: {self.BRANCO}https://{domain}{self.RESET}")
        print(f"   {self.VERDE}📧{self.RESET} Email: {self.BRANCO}{credentials['email']}{self.RESET}")
        print(f"   {self.VERDE}🔐{self.RESET} Senha: {self.BRANCO}{'*' * len(credentials['password'])}{self.RESET}")
        print()
        print(f"{self.BEGE}💡 DICA: As credenciais foram salvas em:{self.RESET}")
        print(f"   {self.CINZA}/root/livchat-config.json{self.RESET}")
        print()
        print(f"{self.VERDE}🚀 Acesse o Chatwoot e faça login com as credenciais acima!{self.RESET}")
        print()
        
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para finalizar...{self.RESET}")
    
    def find_chatwoot_container(self, max_wait_time=300, wait_interval=10):
        """Encontra o container do Chatwoot app aguardando até ele estar disponível"""
        import time
        import subprocess
        
        self.logger.info("Aguardando container do Chatwoot ficar disponível...")
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                result = subprocess.run(
                    "docker ps -q --filter 'name=chatwoot_chatwoot_app'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    container_id = result.stdout.strip()
                    
                    # Verifica se o container está realmente pronto
                    if self._is_container_ready(container_id):
                        self.logger.info(f"Container pronto: {container_id}")
                        return container_id
                    else:
                        self.logger.info(f"Container encontrado mas ainda não está pronto: {container_id}")
                    
            except Exception as e:
                self.logger.debug(f"Erro ao procurar container: {e}")
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval
            
            if elapsed_time % 60 == 0:  # Log a cada minuto
                self.logger.info(f"Aguardando... ({elapsed_time}/{max_wait_time}s)")
        
        self.logger.error(f"Container não encontrado após {max_wait_time} segundos")
        return None
    
    def _is_container_ready(self, container_id):
        """Verifica se o container está pronto para receber comandos"""
        import subprocess
        
        try:
            # Tenta executar um comando simples para verificar se o container responde
            result = subprocess.run(
                f"docker exec {container_id} echo 'ready'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "ready" in result.stdout
        except Exception:
            return False
    
    def _fix_postgres_password(self):
        """Corrige a senha do usuário postgres no banco de dados"""
        import subprocess
        
        try:
            # Obtém a senha do PgVector
            pgvector_password = self._get_pgvector_password()
            if not pgvector_password:
                self.logger.error("Não foi possível obter a senha do PgVector")
                return False
            
            # Encontra o container do PgVector
            result = subprocess.run(
                "docker ps -q --filter 'name=pgvector_pgvector'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                self.logger.error("Container do PgVector não encontrado")
                return False
            
            pgvector_container = result.stdout.strip()
            
            # Atualiza a senha do usuário postgres
            self.logger.info("Corrigindo senha do usuário postgres no banco de dados")
            result = subprocess.run(
                f"docker exec {pgvector_container} psql -U postgres -c \"ALTER USER postgres PASSWORD '{pgvector_password}';\"",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.logger.info("Senha do PostgreSQL corrigida com sucesso")
                return True
            else:
                self.logger.error(f"Erro ao corrigir senha do PostgreSQL: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante correção da senha do PostgreSQL: {e}")
            return False
    
    def unlock_super_admin_functions(self):
        """
        Desbloqueia funções do super admin para permitir criação da primeira conta.
        
        FUNCIONALIDADE:
        - Define installation_configs.locked = false no banco de dados
        - Permite que o Chatwoot mostre a página de onboarding (/installation/onboarding)
        - Sem isso, o Chatwoot assume que já foi configurado e vai direto para login
        - Facilita o processo de instalação evitando criação manual de conta no DB
        
        NOTA: Atualmente comentado pois rails db:chatwoot_prepare já resolve o problema.
        Mantido para compatibilidade futura ou casos específicos.
        """
        import subprocess
        
        try:
            # Encontra o container do PgVector
            result = subprocess.run(
                "docker ps -q --filter 'name=pgvector'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                self.logger.error("Container do PgVector não encontrado")
                return False
            
            pgvector_container = result.stdout.strip()
            
            # Executa o comando SQL para desbloquear installation_configs
            self.logger.info("Desbloqueando funções do super admin...")
            
            # Comando SQL corrigido - usando PGPASSWORD e comando separado
            pgvector_password = self._get_pgvector_password()
            sql_commands = [
                f"docker exec -i {pgvector_container} psql -U postgres -d chatwoot -c \"UPDATE installation_configs SET locked = false;\""
            ]
            
            for sql_command in sql_commands:
                result = subprocess.run(
                    sql_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={'PGPASSWORD': pgvector_password}
                )
                
                if result.returncode == 0:
                    self.logger.info("[ OK ] - Desbloqueando tabela installation_configs no pgvector")
                    return True
                else:
                    self.logger.error("[ ERRO ] - Falha ao desbloquear tabela installation_configs")
                    self.logger.error(f"Erro: {result.stderr}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro ao desbloquear funções do super admin: {e}")
            return False

    def run_database_migrations(self):
        """Executa as migrações do banco de dados do Chatwoot"""
        import subprocess
        
        # Encontra o container do Chatwoot
        container_id = self.find_chatwoot_container()
        if not container_id:
            return False
        
        # Corrige a senha do PostgreSQL no banco
        if not self._fix_postgres_password():
            self.logger.warning("Não foi possível corrigir a senha do PostgreSQL, tentando continuar...")
        
        try:
            # Executa rails db:chatwoot_prepare (comando específico do Chatwoot para setup inicial)
            self.logger.info("Executando: bundle exec rails db:chatwoot_prepare")
            result = subprocess.run(
                f"docker exec {container_id} bundle exec rails db:chatwoot_prepare",
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.logger.info("[ OK ] - Executando: bundle exec rails db:chatwoot_prepare")
                
                # OPCIONAL: Desbloqueia funções do super admin (permite criação da primeira conta)
                # Comentado pois rails db:chatwoot_prepare já resolve o problema na maioria dos casos
                # Descomente se necessário para casos específicos:
                # if self.unlock_super_admin_functions():
                #     self.logger.info("Super admin desbloqueado com sucesso")
                # else:
                #     self.logger.warning("Falha ao desbloquear super admin (não crítico)")
                
                self.logger.info("Setup inicial do Chatwoot concluído com sucesso")
                return True
            else:
                self.logger.error("[ ERRO ] - Falha no setup inicial do Chatwoot")
                self.logger.error(f"Erro: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante migrações: {e}")
            return False
