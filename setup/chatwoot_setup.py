#!/usr/bin/env python3

import subprocess
import logging
import os
from .base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from setup.pgvector_setup import PgVectorSetup
from utils.cloudflare_api import get_cloudflare_api
from utils.config_manager import ConfigManager

class ChatwootSetup(BaseSetup):
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
            installer = PgVectorSetup(network_name=self.network_name)
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
            # Primeiro tenta do ConfigManager
            pgvector_creds = self.config.get_app_credentials("pgvector")
            if pgvector_creds.get("password"):
                return pgvector_creds["password"]
            
            # Fallback para arquivo antigo
            with open("/root/dados_vps/dados_pgvector", 'r') as f:
                for line in f:
                    if line.startswith("Senha:"):
                        return line.split(":", 1)[1].strip()
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do PgVector: {e}")
        return ""

    def collect_user_inputs(self) -> dict:
        """Coleta informações do usuário com sugestões automáticas"""
        print(f"\n💬 CONFIGURAÇÃO CHATWOOT")
        print("─" * 30)
        
        # Domínio sugerido
        suggested_domain = self.config.suggest_domain("chatwoot")
        domain = input(f"Domínio (Enter para '{suggested_domain}' ou digite outro): ").strip()
        if not domain:
            domain = suggested_domain
        
        # Email e senha sugeridos
        suggested_email, suggested_password = self.config.get_suggested_email_and_password("chatwoot")
        
        smtp_email = input(f"Email SMTP (Enter para '{suggested_email}' ou digite outro): ").strip()
        if not smtp_email:
            smtp_email = suggested_email
            
        smtp_user = input(f"Usuário SMTP (Enter para '{smtp_email}' ou digite outro): ").strip()
        if not smtp_user:
            smtp_user = smtp_email
            
        print(f"\n⚠️  Senha SMTP sugerida (64 caracteres seguros): {suggested_password}")
        smtp_password = input("Digite a senha SMTP (Enter para usar a sugerida): ").strip()
        if not smtp_password:
            smtp_password = suggested_password
            
        smtp_host = input("Host SMTP (ex: smtp.hostinger.com): ").strip()
        smtp_port = input("Porta SMTP (Enter para '465' ou digite outra): ").strip()
        if not smtp_port:
            smtp_port = "465"
        
        # Dados computados
        try:
            result = subprocess.run("hostname", shell=True, capture_output=True, text=True)
            company_name = result.stdout.strip() if result.returncode == 0 else "Empresa"
        except:
            company_name = "Empresa"
        
        smtp_domain = smtp_email.split("@")[1] if "@" in smtp_email else ""
        smtp_ssl = "true" if smtp_port == "465" else "false"
        
        # Confirmação com mais detalhes
        print(f"\n📋 RESUMO DA CONFIGURAÇÃO")
        print("─" * 30)
        print(f"🌍 Domínio: {domain}")
        print(f"📧 Email SMTP: {smtp_email}")
        print(f"📮 Host SMTP: {smtp_host}:{smtp_port}")
        
        # Avisar sobre DNS automático
        if self.config.is_cloudflare_auto_dns_enabled():
            print(f"✅ DNS será configurado automaticamente via Cloudflare")
        else:
            print(f"⚠️  Você precisará configurar o DNS manualmente")
            
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm not in ['s', 'sim', 'y', 'yes']:
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
        cf = get_cloudflare_api(self.config, self.logger)
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
