#!/usr/bin/env python3
"""
Módulo de setup do Directus
Baseado no padrão do Chatwoot e N8N, reutilizando PostgreSQL + PgVector
Inclui integração com Cloudflare para DNS automático
"""

import subprocess
from .base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.cloudflare_api import get_cloudflare_api
from setup.pgvector_setup import PgVectorSetup
from utils.config_manager import ConfigManager

class DirectusSetup(BaseSetup):
    def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do Directus")
        self.portainer = PortainerAPI()
        self.config = config_manager or ConfigManager()
        self.network_name = network_name

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

    def is_docker_running(self) -> bool:
        """Verifica se Docker está rodando (mesma abordagem de outros módulos)"""
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

    def collect_user_inputs(self) -> dict:
        """Coleta informações do usuário com sugestões automáticas"""
        print(f"\n📝 CONFIGURAÇÃO DIRECTUS")
        print("─" * 30)
        
        # Domínio sugerido
        suggested_domain = self.config.suggest_domain("directus")
        domain = input(f"Domínio (Enter para '{suggested_domain}' ou digite outro): ").strip()
        if not domain:
            domain = suggested_domain
        
        # Email e senha sugeridos
        suggested_email, suggested_password = self.config.get_suggested_email_and_password("directus")
        
        admin_email = input(f"Email do Admin (Enter para '{suggested_email}' ou digite outro): ").strip()
        if not admin_email:
            admin_email = suggested_email
        
        print(f"\n⚠️  Senha do Admin sugerida (64 caracteres seguros): {suggested_password}")
        admin_password = input("Digite a senha do Admin (Enter para usar a sugerida): ").strip()
        if not admin_password:
            admin_password = suggested_password

        # Confirmação
        print(f"\n📝 RESUMO DA CONFIGURAÇÃO")
        print("─" * 30)
        print(f"🌍 Domínio: {domain}")
        print(f"📧 Admin Email: {admin_email}")
        
        # Avisar sobre DNS automático
        if self.config.is_cloudflare_auto_dns_enabled():
            print(f"✅ DNS será configurado automaticamente via Cloudflare")
        else:
            print(f"⚠️  Você precisará configurar o DNS manualmente")
        
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm not in ['s', 'sim', 'y', 'yes']:
            return None

        # Gerar encryption key usando ConfigManager
        encryption_key = self.config.generate_secure_password(32)  # 32 chars para encryption key
        pgvector_password = self._get_pgvector_password()
        
        config_data = {
            'domain': domain,
            'admin_email': admin_email,
            'admin_password': admin_password,
            'encryption_key': encryption_key,
            'pgvector_password': pgvector_password,
            'network_name': self.network_name,
            # Diretriz: Directus reutiliza o mesmo database do Chatwoot por padrão
            'database_name': 'chatwoot'
        }
        
        # Salva configuração no ConfigManager
        self.config.save_app_config("directus", {
            "domain": domain,
            "database_name": "chatwoot",
            "admin_email": admin_email
        })
        
        # Salva credenciais no ConfigManager
        self.config.save_app_credentials("directus", {
            "admin_email": admin_email,
            "admin_password": admin_password,
            "encryption_key": encryption_key
        })
        
        return config_data

    def create_database(self) -> bool:
        """Garante que o database 'chatwoot' exista no PgVector (reutilizado pelo Directus)"""
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
                self.logger.info("Banco de dados chatwoot criado/verificado (reutilizado pelo Directus)")
                return True
            else:
                self.logger.warning(f"Aviso ao criar banco: {result.stderr}")
                return True
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
        return cf.create_app_dns_record("directus", domain)

    def run(self) -> bool:
        """Executa instalação do Directus"""
        try:
            if not self.validate_prerequisites():
                return False

            variables = None
            while not variables:
                variables = self.collect_user_inputs()
                if not variables:
                    print("\nVamos tentar novamente...\n")

            # DNS via Cloudflare (não bloqueante)
            if not self.setup_dns_records(variables['domain']):
                self.logger.warning("Falha na configuração DNS, continuando mesmo assim...")

            if not self.create_database():
                self.logger.error("Falha ao criar banco de dados")
                return False

            success = self.portainer.deploy_service_complete(
                service_name="directus",
                template_path="docker-compose/directus.yaml.j2",
                template_vars=variables,
                volumes=[
                    "directus_uploads",
                    "directus_extensions"
                ],
                wait_services=["directus_directus_app"],
                credentials={
                    'domain': variables['domain'],
                    'admin_email': variables['admin_email'],
                    'admin_password': variables['admin_password'],
                    'encryption_key': variables['encryption_key'],
                    'database': variables['database_name']
                }
            )

            if success:
                self.logger.info("Instalação do Directus concluída com sucesso")
                self.logger.info(f"Acesse: https://{variables['domain']}")
                return True
            else:
                self.logger.error("Falha na instalação do Directus")
                return False
        except Exception as e:
            self.logger.error(f"Erro durante instalação do Directus: {e}")
            return False
