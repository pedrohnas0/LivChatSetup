#!/usr/bin/env python3
"""
Módulo de setup do N8N
Baseado na função ferramenta_n8n() do SetupOrionOriginal.sh
Inclui integração com Cloudflare para DNS automático
"""

import os
import secrets
import subprocess
from datetime import datetime
from setup.base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.template_engine import TemplateEngine
from utils.cloudflare_api import get_cloudflare_api
from setup.postgres_setup import PostgresSetup
from setup.redis_setup import RedisSetup
from utils.config_manager import ConfigManager

class N8NSetup(BaseSetup):
    """Setup do N8N com integração Cloudflare"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("N8N (Workflow Automation)")
        self.service_name = "n8n"
        self.portainer_api = PortainerAPI()
        self.template_engine = TemplateEngine()
        self.network_name = network_name
        self.config = config_manager or ConfigManager()
        
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para o N8N"""
        try:
            if not self.network_name:
                self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
                return False

            # Garante PostgreSQL
            if not self.ensure_postgres():
                return False

            # Garante Redis
            if not self.ensure_redis():
                return False

            self.logger.info("✅ Pré-requisitos validados")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao validar pré-requisitos: {e}")
            return False
    
    def run(self) -> bool:
        """Executa o setup do N8N"""
        if not self.validate_prerequisites():
            return False
        
        return self.install()
    
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
        
        # Centralização padrão (mantém original)
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
        
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None) -> str:
        """Coleta entrada do usuário com sugestão opcional seguindo padrão do projeto"""
        try:
            if suggestion:
                full_prompt = f"{prompt} (Enter para '{suggestion}' ou digite outro valor)"
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
        
    def collect_user_inputs(self):
        """Coleta informações do usuário para o N8N seguindo padrão do projeto"""
        self._print_section_box("⚙️  CONFIGURAÇÃO N8N")
        
        # Domínio do N8N Editor com sugestão inteligente
        n8n_suggested_domain = self._get_domain_suggestion('n8n_domain', 'edt')
        while True:
            n8n_domain = self.get_user_input("Domínio do N8N Editor", suggestion=n8n_suggested_domain)
            if n8n_domain and '.' in n8n_domain:
                break
            print(f"{self.VERMELHO}❌ Domínio é obrigatório e deve ser válido!{self.RESET}")
        
        # Domínio do Webhook com sugestão inteligente
        webhook_suggested_domain = self._get_domain_suggestion('webhook_domain', 'whk')
        while True:
            webhook_domain = self.get_user_input("Domínio do Webhook do N8N", suggestion=webhook_suggested_domain)
            if webhook_domain and '.' in webhook_domain:
                break
            print(f"{self.VERMELHO}❌ Domínio do webhook é obrigatório e deve ser válido!{self.RESET}")
        
        # Obtém configuração SMTP do ConfigManager
        smtp_config = self.config.get_app_config("smtp")
        if not smtp_config or not smtp_config.get("configured", False):
            self._print_section_box("⚠️  SMTP NÃO CONFIGURADO")
            print(f"{self.VERMELHO}❌ N8N precisa de configuração SMTP para envio de emails!{self.RESET}")
            print(f"{self.BEGE}Configure o SMTP primeiro no menu principal (item 2).{self.RESET}")
            print()
            
            configure_now = self.get_user_input("Deseja configurar SMTP agora", suggestion="sim")
            if configure_now and configure_now.lower() in ['sim', 's', 'yes', 'y']:
                from setup.smtp_setup import SMTPSetup
                smtp_setup = SMTPSetup(config_manager=self.config)
                if not smtp_setup.run():
                    print(f"{self.VERMELHO}❌ Falha na configuração SMTP. N8N não pode prosseguir.{self.RESET}")
                    return None
                # Recarrega configuração após setup
                smtp_config = self.config.get_app_config("smtp")
            else:
                print(f"{self.VERMELHO}❌ N8N cancelado. Configure SMTP primeiro.{self.RESET}")
                return None
        
        self._print_section_box("✅ SMTP CONFIGURADO")
        print(f"{self.VERDE}📧{self.RESET} Servidor: {smtp_config['smtp_host']}:{smtp_config['smtp_port']}")
        print(f"{self.VERDE}📨{self.RESET} Remetente: {smtp_config['sender_email']}")
        print()
        
        # Converte configurações para formato do N8N
        smtp_email = smtp_config['sender_email']
        smtp_user = smtp_config['smtp_username']
        smtp_password = smtp_config['smtp_password']
        smtp_host = smtp_config['smtp_host']
        smtp_port = smtp_config['smtp_port']
        smtp_secure = smtp_config['smtp_ssl']
        
        # Confirmação visual melhorada
        self._print_section_box("📋 CONFIRMAÇÃO DAS CONFIGURAÇÕES")
        print(f"{self.VERDE}🌐{self.RESET} Domínio N8N: {self.BRANCO}{n8n_domain}{self.RESET}")
        print(f"{self.VERDE}🔗{self.RESET} Domínio Webhook: {self.BRANCO}{webhook_domain}{self.RESET}")
        print()
        print(f"{self.BEGE}📧 SMTP (obtido da configuração centralizada):{self.RESET}")
        print(f"{self.VERDE}  📨{self.RESET} Servidor: {self.BRANCO}{smtp_host}:{smtp_port}{self.RESET}")
        print(f"{self.VERDE}  📧{self.RESET} Remetente: {self.BRANCO}{smtp_email}{self.RESET}")
        ssl_method = "SSL/TLS" if smtp_secure == "true" else "STARTTLS"
        print(f"{self.VERDE}  🔒{self.RESET} Segurança: {self.BRANCO}{ssl_method}{self.RESET}")
        print()
        print(f"{self.BEGE}Pressione {self.VERDE}Enter{self.BEGE} para confirmar · {self.VERMELHO}Esc{self.BEGE} para corrigir dados{self.RESET}")
        
        try:
            import termios
            import tty
            import sys
            
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            try:
                tty.setcbreak(sys.stdin.fileno())
                while True:
                    key = sys.stdin.read(1)
                    
                    if ord(key) == 10 or ord(key) == 13:  # Enter
                        print("✅ Configurações confirmadas!")
                        break
                    elif ord(key) == 27:  # Esc
                        print("❌ Voltando para corrigir dados...")
                        self.logger.info("Usuário solicitou correção das configurações")
                        return None
                    elif key.lower() == 'q':  # Q para quit
                        print("❌ Configuração cancelada")
                        self.logger.info("Instalação cancelada pelo usuário")
                        return None
                        
            finally:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
                
        except ImportError:
            # Fallback para sistemas sem termios
            confirm = input("Confirmar? (Enter=Sim, N=Não): ").strip()
            if confirm and confirm.lower() not in ['', 'sim', 's', 'yes', 'y']:
                self.logger.info("Instalação cancelada pelo usuário")
                return None
            
        return {
            'n8n_domain': n8n_domain,
            'webhook_domain': webhook_domain,
            'smtp_email': smtp_email,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_secure': smtp_secure
        }
    
    def setup_dns_records(self, n8n_domain, webhook_domain):
        """Configura registros DNS via Cloudflare"""
        self.logger.info("Configurando registros DNS via Cloudflare...")
        
        # Obtém instância da Cloudflare API
        cf = get_cloudflare_api(self.logger)
        if not cf:
            self.logger.error("Falha ao inicializar Cloudflare API")
            return False
        
        # Configura DNS para o serviço N8N
        domains = [n8n_domain, webhook_domain]
        return cf.setup_dns_for_service("N8N", domains)
    
    def _get_domain_suggestion(self, domain_key: str, subdomain_prefix: str) -> str:
        """Gera sugestão de domínio inteligente baseada em configurações existentes"""
        try:
            # Verifica se já existe configuração do N8N
            existing_config = self.config.get_app_config('n8n')
            if existing_config and domain_key in existing_config:
                return existing_config[domain_key]
            
            # Fallback: constrói baseado nas configurações globais usando Cloudflare zone_name
            cloudflare_config = self.config.get_cloudflare_config()
            zone_name = cloudflare_config.get('zone_name', '')
            default_subdomain = self.config.get_default_subdomain() or 'dev'
            
            if zone_name:
                return f"{subdomain_prefix}.{default_subdomain}.{zone_name}"
            else:
                # Se não há Cloudflare configurado, usar hostname como fallback
                hostname = self.config.get_hostname() or 'localhost'
                return f"{subdomain_prefix}.{default_subdomain}.{hostname}"
        except Exception as e:
            self.logger.error(f"Erro ao gerar sugestão de domínio: {e}")
            return f"{subdomain_prefix}.dev.localhost"
    
    def get_postgres_password(self):
        """Obtém a senha do PostgreSQL via ConfigManager"""
        try:
            # Primeiro tenta do ConfigManager
            postgres_creds = self.config.get_app_credentials('postgres')
            if postgres_creds and 'password' in postgres_creds:
                return postgres_creds['password']
            
            
            self.logger.error("Credenciais do PostgreSQL não encontradas")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do PostgreSQL: {e}")
            return None
    
    def get_redis_password(self):
        """Obtém a senha do Redis via ConfigManager"""
        try:
            # Primeiro tenta do ConfigManager
            redis_creds = self.config.get_app_credentials('redis')
            if redis_creds and 'password' in redis_creds:
                return redis_creds['password']
            
            
            self.logger.error("Credenciais do Redis não encontradas")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do Redis: {e}")
            return None
    
    def create_database(self, database_name):
        """Cria banco de dados no PostgreSQL"""
        postgres_password = self.get_postgres_password()
        if not postgres_password:
            return False
        
        try:
            # Encontra container da task do serviço Swarm 'postgres_postgres'
            result = subprocess.run(
                "bash -lc \"docker ps --format '{{.Names}}' | grep -E '^postgres_postgres\\.' | head -n1\"",
                shell=True,
                capture_output=True,
                text=True
            )

            container_name = result.stdout.strip()
            if not container_name:
                self.logger.error("Container do serviço PostgreSQL não encontrado")
                return False
            
            # Limpa possíveis tipos conflitantes da database postgres que podem ter sido deixados por instalações anteriores
            clean_types_cmd = f"""docker exec {container_name} psql -U postgres -c "DROP TYPE IF EXISTS project CASCADE;" """
            subprocess.run(clean_types_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
            
            # Verifica se banco de dados existe
            check_db_cmd = f"docker exec {container_name} psql -U postgres -t -c \"SELECT 1 FROM pg_database WHERE datname = '{database_name}';\""
            
            result = subprocess.run(check_db_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
            
            if result.stdout.strip():
                self.logger.info(f"⚠️ Banco de dados '{database_name}' já existe, removendo para garantir instalação limpa")
                
                # Remove conexões ativas e dropa o banco
                drop_connections_cmd = f"""docker exec {container_name} psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{database_name}' AND pid <> pg_backend_pid();" """
                subprocess.run(drop_connections_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
                
                # Aguarda um pouco para garantir que conexões foram fechadas
                import time
                time.sleep(2)
                
                drop_db_cmd = f"docker exec {container_name} psql -U postgres -c \"DROP DATABASE IF EXISTS {database_name};\""
                result_drop = subprocess.run(drop_db_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
                
                if result_drop.returncode == 0:
                    self.logger.info(f"🧹 Banco de dados '{database_name}' removido com sucesso")
                else:
                    self.logger.warning(f"Aviso ao remover banco: {result_drop.stderr}")
            
            # Cria o banco se não existir
            create_db_cmd = f"docker exec {container_name} psql -U postgres -c \"CREATE DATABASE {database_name};\""
            
            self.logger.info(f"🔧 Criando banco de dados limpo '{database_name}'...")
            
            result = subprocess.run(create_db_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
            
            if result.returncode == 0:
                self.logger.info(f"✅ Banco de dados '{database_name}' criado com sucesso")
                return True
            else:
                self.logger.error(f"Erro ao criar banco: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao criar banco de dados: {e}")
            return False

    def ensure_postgres(self) -> bool:
        """Garante que o PostgreSQL esteja instalado e rodando; instala se necessário."""
        # Verifica serviço do Swarm
        check = subprocess.run(
            "docker service ps postgres_postgres --format '{{.CurrentState}}'",
            shell=True,
            capture_output=True,
            text=True
        )
        if check.returncode != 0 or "Running" not in check.stdout:
            self.logger.warning("PostgreSQL não encontrado/rodando. Iniciando instalação automática...")
            pg = PostgresSetup(network_name=self.network_name, config_manager=self.config)
            if not pg.run():
                self.logger.error("Falha ao instalar/configurar PostgreSQL")
                return False
        return True

    def ensure_redis(self) -> bool:
        """Garante que o Redis esteja instalado e rodando; instala se necessário."""
        check = subprocess.run(
            "docker service ps redis_redis --format '{{.CurrentState}}'",
            shell=True,
            capture_output=True,
            text=True
        )
        if check.returncode != 0 or "Running" not in check.stdout:
            self.logger.warning("Redis não encontrado/rodando. Iniciando instalação automática...")
            rd = RedisSetup(network_name=self.network_name, config_manager=self.config)
            if not rd.run():
                self.logger.error("Falha ao instalar/configurar Redis")
                return False
        return True
    
    def install(self):
        """Instala o N8N"""
        try:
            # Loop de coleta e confirmação de configurações
            while True:
                # Coleta dados do usuário
                user_data = self.collect_user_inputs()
                if not user_data:
                    return False
                
                # Se chegou até aqui, os dados foram confirmados
                break
            
            self.logger.info("Iniciando instalação do N8N...")
            
            # Configura DNS via Cloudflare
            if not self.setup_dns_records(user_data['n8n_domain'], user_data['webhook_domain']):
                self.logger.warning("Falha na configuração DNS, mas continuando...")
            
            # Verifica/cria banco de dados
            database_name = "n8n_queue"
            if not self.create_database(database_name):
                self.logger.error("Falha ao criar banco de dados")
                return False
            
            # Obtém senha do PostgreSQL
            postgres_password = self.get_postgres_password()
            if not postgres_password:
                self.logger.error("Falha ao obter senha do PostgreSQL")
                return False
            
            # Obtém senha do Redis
            redis_password = self.get_redis_password()
            if not redis_password:
                self.logger.error("Falha ao obter senha do Redis")
                return False
            
            # Gera chave de criptografia
            encryption_key = secrets.token_hex(16)
            
            # Prepara variáveis para o template
            variables = {
                'network_name': self.network_name,
                'database_name': database_name,
                'postgres_password': postgres_password,
                'redis_password': redis_password,
                'encryption_key': encryption_key,
                'n8n_domain': user_data['n8n_domain'],
                'webhook_domain': user_data['webhook_domain'],
                'smtp_email': user_data['smtp_email'],
                'smtp_user': user_data['smtp_user'],
                'smtp_password': user_data['smtp_password'],
                'smtp_host': user_data['smtp_host'],
                'smtp_port': user_data['smtp_port'],
                'smtp_secure': user_data['smtp_secure']
            }
            
            # Deploy via Portainer
            services_to_wait = ['n8n_n8n_editor', 'n8n_n8n_webhook', 'n8n_n8n_worker']
            
            success = self.portainer_api.deploy_service_complete(
                service_name="n8n",
                template_path="docker-compose/n8n.yaml.j2",
                template_vars=variables,
                wait_services=services_to_wait,
                credentials={
                    'n8n_domain': user_data['n8n_domain'],
                    'webhook_domain': user_data['webhook_domain'],
                    'encryption_key': encryption_key,
                    'database_name': database_name,
                    'smtp_email': user_data['smtp_email'],
                    'smtp_host': user_data['smtp_host'],
                    'smtp_port': user_data['smtp_port']
                }
            )
            
            if success:
                # Salva configuração do N8N no ConfigManager
                config_data = {
                    'n8n_domain': user_data['n8n_domain'],
                    'webhook_domain': user_data['webhook_domain'],
                    'database_name': database_name,
                    'configured_at': datetime.now().isoformat()
                }
                self.config.save_app_config('n8n', config_data)
                
                # Salva credenciais do N8N no ConfigManager
                credentials = {
                    'n8n_domain': user_data['n8n_domain'],
                    'webhook_domain': user_data['webhook_domain'],
                    'encryption_key': encryption_key,
                    'database_name': database_name,
                    'smtp_email': user_data['smtp_email'],
                    'smtp_host': user_data['smtp_host'],
                    'smtp_port': user_data['smtp_port'],
                    'smtp_secure': user_data['smtp_secure'],
                    'created_at': datetime.now().isoformat()
                }
                self.config.save_app_credentials('n8n', credentials)
                
                self.logger.info("Credenciais de n8n salvas no ConfigManager centralizado")
                
                self.logger.info("Instalação do N8N concluída com sucesso")
                
                # Sessão de sucesso para configurar conta inicial
                self._show_success_session(user_data['n8n_domain'])
                
                return True
            else:
                self.logger.error("Falha na instalação do N8N")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante instalação do N8N: {e}")
            return False
    
    def _show_success_session(self, n8n_domain: str):
        """Exibe sessão de sucesso para configurar conta inicial do N8N"""
        self._print_section_box("✅ N8N INSTALADO COM SUCESSO!")
        
        print(f"{self.VERDE}🌐 URL de Acesso: {self.BRANCO}https://{n8n_domain}{self.RESET}")
        print()
        print(f"{self.BEGE}📝 PRÓXIMO PASSO: Configure sua conta de administrador no N8N{self.RESET}")
        print()
        
        # Gera credenciais sugeridas usando ConfigManager
        suggested_credentials = self._generate_suggested_credentials()
        
        print(f"{self.BEGE}👤 DADOS SUGERIDOS PARA A CONTA:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Email: {self.BRANCO}{suggested_credentials['email']}{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Senha: {self.BRANCO}{suggested_credentials['password']}{self.RESET}")
        
        # Só mostra nome se já existe no config
        if self._has_user_name_configured():
            print(f"   {self.VERDE}•{self.RESET} Primeiro Nome: {self.BRANCO}{suggested_credentials['first_name']}{self.RESET}")
            print(f"   {self.VERDE}•{self.RESET} Último Nome: {self.BRANCO}{suggested_credentials['last_name']}{self.RESET}")
        
        print()
        
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para continuar...{self.RESET}")
        
        # Coleta credenciais confirmadas pelo usuário
        final_credentials = self._collect_n8n_account_data(suggested_credentials)
        
        if final_credentials:
            self._save_n8n_account_credentials(final_credentials)
            self._show_final_summary(n8n_domain, final_credentials)
    
    def _generate_suggested_credentials(self) -> dict:
        """Gera credenciais sugeridas para conta do N8N"""
        email = self.config.get_user_email() or "admin@livchat.ai"
        password = self.config.generate_secure_password(64)  # 64 caracteres como solicitado
        
        # Obtém dados do usuário apenas se existirem no config
        user_data = self.config.config_data["global"]
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        
        # Só inclui nomes se existirem no config (não gera sugestões automáticas)
        result = {
            "email": email,
            "password": password
        }
        
        if first_name:
            result["first_name"] = first_name
        if last_name:
            result["last_name"] = last_name
        
        return result
    
    def _has_user_name_configured(self) -> bool:
        """Verifica se há primeiro ou último nome configurado"""
        user_data = self.config.config_data["global"]
        return bool(user_data.get("first_name") or user_data.get("last_name"))
    
    def _collect_n8n_account_data(self, suggested_credentials: dict) -> dict:
        """Coleta dados da conta do N8N com sugestões"""
        self._print_section_box("👤 CONFIGURE SUA CONTA N8N")
        
        print(f"{self.BEGE}Confirme os dados para sua conta de administrador no N8N:{self.RESET}")
        print(f"{self.BEGE}(Enter para aceitar sugestão, outro valor para alterar, ESC para pular campo){self.RESET}")
        print()
        
        # Email
        email = self._get_user_input_with_escape(
            "Email", 
            suggestion=suggested_credentials['email']
        )
        
        # Senha
        password = self._get_user_input_with_escape(
            "Senha", 
            suggestion=suggested_credentials['password']
        )
        
        # Nomes só se já estiverem configurados
        first_name = None
        last_name = None
        
        if self._has_user_name_configured():
            # Primeiro nome
            first_name = self._get_user_input_with_escape(
                "Primeiro Nome", 
                suggestion=suggested_credentials['first_name']
            )
            
            # Último nome  
            last_name = self._get_user_input_with_escape(
                "Último Nome", 
                suggestion=suggested_credentials['last_name']
            )
        
        return {
            "email": email or suggested_credentials['email'],
            "password": password or suggested_credentials['password'],
            "first_name": first_name or suggested_credentials.get('first_name', ''),
            "last_name": last_name or suggested_credentials.get('last_name', '')
        }
    
    def _get_user_input_with_escape(self, prompt: str, suggestion: str = None) -> str:
        """Versão simplificada de input com sugestão e escape"""
        try:
            if suggestion:
                full_prompt = f"{prompt} (Enter para '{suggestion}', outro valor para alterar, ESC para pular)"
            else:
                full_prompt = prompt
                
            print(f"{self.BEGE}{full_prompt}:{self.RESET}", end=" ")
            
            # Input simples - implementação básica
            value = input().strip()
            
            # Se não digitou nada e há sugestão, usa a sugestão
            if not value and suggestion:
                return suggestion
                
            return value if value else None
            
        except KeyboardInterrupt:
            print(f"\n{self.VERMELHO}Operação cancelada pelo usuário.{self.RESET}")
            return None
    
    def _save_n8n_account_credentials(self, credentials: dict):
        """Salva credenciais da conta do N8N"""
        # Salva dados da conta do usuário no ConfigManager
        account_data = {
            'email': credentials['email'],
            'password': credentials['password'],
            'first_name': credentials['first_name'],
            'last_name': credentials['last_name'],
            'created_at': datetime.now().isoformat()
        }
        
        # Atualiza credenciais do N8N com dados da conta
        existing_creds = self.config.get_app_credentials('n8n')
        existing_creds.update({
            'account_email': credentials['email'],
            'account_password': credentials['password'],
            'account_first_name': credentials['first_name'],
            'account_last_name': credentials['last_name']
        })
        self.config.save_app_credentials('n8n', existing_creds)
        
        # Atualiza dados globais do usuário se necessário
        self.config.config_data["global"]["first_name"] = credentials['first_name']
        self.config.config_data["global"]["last_name"] = credentials['last_name']
        self.config.save_config()
        
        self.logger.info("Dados da conta N8N salvos no ConfigManager")
    
    def _show_final_summary(self, n8n_domain: str, credentials: dict):
        """Exibe resumo final da instalação"""
        self._print_section_box("🎉 N8N PRONTO PARA USO!")
        
        print(f"{self.VERDE}🌐 URL: {self.BRANCO}https://{n8n_domain}{self.RESET}")
        print(f"{self.VERDE}📧 Email: {self.BRANCO}{credentials['email']}{self.RESET}")
        
        # Só mostra nome se houver
        if credentials.get('first_name') or credentials.get('last_name'):
            full_name = f"{credentials.get('first_name', '')} {credentials.get('last_name', '')}".strip()
            if full_name:
                print(f"{self.VERDE}👤 Nome: {self.BRANCO}{full_name}{self.RESET}")
        
        print()
        print(f"{self.BEGE}📝 INSTRUÇÕES:{self.RESET}")
        print(f"   {self.VERDE}1.{self.RESET} Acesse {self.BRANCO}https://{n8n_domain}{self.RESET}")
        print(f"   {self.VERDE}2.{self.RESET} Crie sua conta com os dados confirmados acima")
        print(f"   {self.VERDE}3.{self.RESET} Comece a criar seus workflows de automação")
        print()
        print(f"{self.LARANJA}✨ N8N configurado e pronto para automações!{self.RESET}")
        print()
        
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para instalar mais aplicações ou {self.VERMELHO}Ctrl+C{self.RESET} {self.BEGE}para encerrar...{self.RESET}")
    
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
        
        # Centralização perfeita usando Python nativo
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplica cor ao título
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
        
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback padrão
