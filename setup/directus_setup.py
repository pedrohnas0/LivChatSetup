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

class DirectusSetup(BaseSetup):
    def __init__(self, network_name: str = None):
        super().__init__("Instalação do Directus")
        self.portainer = PortainerAPI()
        self.network_name = network_name

    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
        if not self._is_pgvector_running():
            self.logger.error("PgVector não está instalado. Execute primeiro a instalação do PgVector.")
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

    def _get_pgvector_password(self) -> str:
        """Obtém senha do PgVector"""
        try:
            with open("/root/dados_vps/dados_pgvector", 'r') as f:
                for line in f:
                    if line.startswith("Senha:"):
                        return line.split(":", 1)[1].strip()
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do PgVector: {e}")
        return ""

    def collect_user_inputs(self) -> dict:
        """Coleta informações do usuário e retorna dicionário com variáveis"""
        print("\n=== Configuração do Directus ===")
        domain = input("Digite o domínio para o Directus (ex: cms.seudominio.com): ").strip()
        admin_email = input("Digite o email do Admin do Directus: ").strip()
        admin_password = input("Digite a senha do Admin do Directus: ").strip()

        # Confirmação
        print("\n=== Confirmação ===")
        print(f"Domínio: {domain}")
        print(f"Admin Email: {admin_email}")
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm not in ['s', 'sim', 'y', 'yes']:
            return None

        encryption_key = self.portainer.generate_hex_key(16)
        pgvector_password = self._get_pgvector_password()

        return {
            'domain': domain,
            'admin_email': admin_email,
            'admin_password': admin_password,
            'encryption_key': encryption_key,
            'pgvector_password': pgvector_password,
            'network_name': self.network_name,
            # Diretriz: Directus reutiliza o mesmo database do Chatwoot por padrão
            'database_name': 'chatwoot'
        }

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
        """Configura registros DNS via Cloudflare"""
        self.logger.info("Configurando registros DNS via Cloudflare...")
        cf = get_cloudflare_api(self.logger)
        if not cf:
            self.logger.error("Falha ao inicializar Cloudflare API")
            return False
        return cf.setup_dns_for_service("Directus", [domain])

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
