#!/usr/bin/env python3
"""
Módulo de setup da Evolution API v2
Baseado no script Orion original e seguindo o padrão dos módulos existentes.
Inclui integração com PostgreSQL, Redis e Cloudflare para DNS automático.
"""

import subprocess
import os
import secrets
from urllib.parse import quote
from .base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.cloudflare_api import get_cloudflare_api
from setup.postgres_setup import PostgresSetup
from setup.redis_setup import RedisSetup


class EvolutionSetup(BaseSetup):
    def __init__(self, network_name: str = None):
        super().__init__("Evolution API v2")
        self.portainer_api = PortainerAPI()
        self.network_name = network_name

    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para a Evolution API"""
        if not self._is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
        
        # Garante PostgreSQL (instala automaticamente se necessário)
        if not self._ensure_postgres():
            return False
            
        # Garante Redis (instala automaticamente se necessário)
        if not self._ensure_redis():
            return False
            
        return True

    def _is_docker_running(self) -> bool:
        try:
            result = subprocess.run(
                "docker info",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _is_postgres_running(self) -> bool:
        """Verifica se PostgreSQL está rodando"""
        try:
            result = subprocess.run(
                "docker service ls --filter name=postgres --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return "postgres" in result.stdout
        except Exception:
            return False

    def _is_redis_running(self) -> bool:
        """Verifica se Redis está rodando"""
        try:
            result = subprocess.run(
                "docker service ls --filter name=redis --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return "redis" in result.stdout
        except Exception:
            return False

    def _ensure_postgres(self) -> bool:
        """Garante que PostgreSQL está instalado e rodando"""
        if self._is_postgres_running():
            self.logger.info("✅ PostgreSQL já está rodando")
            return True
        
        self.logger.info("🔧 Instalando PostgreSQL...")
        postgres_setup = PostgresSetup(self.network_name)
        if not postgres_setup.run():
            self.logger.error("❌ Falha ao instalar PostgreSQL")
            return False
        
        self.logger.info("✅ PostgreSQL instalado com sucesso")
        return True

    def _ensure_redis(self) -> bool:
        """Garante que Redis está instalado e rodando"""
        if self._is_redis_running():
            self.logger.info("✅ Redis já está rodando")
            return True
        
        self.logger.info("🔧 Instalando Redis...")
        redis_setup = RedisSetup(self.network_name)
        if not redis_setup.run():
            self.logger.error("❌ Falha ao instalar Redis")
            return False
        
        self.logger.info("✅ Redis instalado com sucesso")
        return True

    def collect_user_inputs(self):
        """Coleta informações do usuário"""
        print("\n=== Configuração da Evolution API v2 ===")

        # Domínio da Evolution API
        while True:
            domain = input("Digite o domínio para a Evolution API (ex: api.seudominio.com): ").strip()
            if domain:
                break
            print("❌ Domínio é obrigatório!")

        # Confirmação
        print("\n=== Resumo ===")
        print(f"Domínio: {domain}")
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm not in ["s", "sim", "y", "yes"]:
            return None

        return {"domain": domain}

    def setup_dns(self, domain: str) -> bool:
        """Configura registros DNS via Cloudflare"""
        self.logger.info("Configurando registros DNS via Cloudflare...")
        cf = get_cloudflare_api(self.logger)
        if not cf:
            self.logger.error("Falha ao inicializar Cloudflare API")
            return False
        return cf.setup_dns_for_service("Evolution API", [domain])

    def _get_postgres_password(self) -> str:
        """Obtém a senha do PostgreSQL do arquivo de credenciais"""
        try:
            creds_path = "/root/dados_vps/dados_postgres"
            if not os.path.exists(creds_path):
                self.logger.error("Arquivo de credenciais do PostgreSQL não encontrado")
                return None
            
            with open(creds_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.lower().startswith('senha:'):
                        return stripped.split(':', 1)[1].strip()
            
            self.logger.error("Senha do PostgreSQL não encontrada no arquivo de credenciais (esperado formato 'Senha: ...')")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao ler credenciais do PostgreSQL: {e}")
            return None

    def _get_redis_password(self) -> str:
        """Obtém a senha do Redis do arquivo de credenciais"""
        try:
            creds_path = "/root/dados_vps/dados_redis"
            if not os.path.exists(creds_path):
                self.logger.error("Arquivo de credenciais do Redis não encontrado")
                return None
            
            with open(creds_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.lower().startswith('senha:'):
                        return stripped.split(':', 1)[1].strip()
            
            self.logger.error("Senha do Redis não encontrada no arquivo de credenciais (esperado formato 'Senha: ...')")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao ler credenciais do Redis: {e}")
            return None

    def _create_database(self, db_name: str) -> bool:
        """Cria banco de dados no PostgreSQL"""
        try:
            postgres_password = self._get_postgres_password()
            if not postgres_password:
                return False

            # Comando para criar banco de dados
            cmd = f"""docker exec -i $(docker ps -q --filter name=postgres) psql -U postgres -c "CREATE DATABASE {db_name};" """
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, 'PGPASSWORD': postgres_password}
            )
            
            if result.returncode == 0 or "already exists" in result.stderr:
                self.logger.info(f"✅ Banco de dados '{db_name}' criado/já existe")
                return True
            else:
                self.logger.error(f"❌ Erro ao criar banco: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar banco de dados: {e}")
            return False

    def run(self) -> bool:
        if not self.validate_prerequisites():
            return False
        return self.install()

    def install(self) -> bool:
        try:
            # Coleta dados do usuário
            variables = None
            while not variables:
                variables = self.collect_user_inputs()
                if not variables:
                    print("\nVamos tentar novamente...\n")

            # DNS (não bloqueante para avanço, mas registra warnings)
            if not self.setup_dns(variables["domain"]):
                self.logger.warning("Falha na configuração DNS, continuando...")

            # Gera API Key global aleatória
            global_api_key = secrets.token_hex(16)
            
            # Obtém senha do PostgreSQL
            postgres_password = self._get_postgres_password()
            if not postgres_password:
                self.logger.error("Não foi possível obter a senha do PostgreSQL")
                return False
            # Obtém senha do Redis
            redis_password = self._get_redis_password()
            if not redis_password:
                self.logger.error("Não foi possível obter a senha do Redis")
                return False
            # Percent-encode para uso seguro em URI
            redis_password_uri = quote(redis_password, safe='')

            # Nome do banco de dados
            database_name = "evolution"
            
            # Cria banco de dados
            if not self._create_database(database_name):
                self.logger.error("Falha ao criar banco de dados")
                return False

            # Variáveis para o template
            template_vars = {
                "network_name": self.network_name,
                "domain": variables["domain"],
                "global_api_key": global_api_key,
                "postgres_password": postgres_password,
                # Use a versão codificada na URI para evitar problemas com caracteres especiais
                "redis_password_uri": redis_password_uri,
                "database_name": database_name,
            }

            # Volumes declarados no compose
            volumes = ["evolution_instances"]

            # Serviços para aguardar
            wait_services = ["evolution_app"]

            # Deploy via Portainer API
            success = self.portainer_api.deploy_service_complete(
                service_name="evolution",
                template_path="docker-compose/evolution.yaml.j2",
                template_vars=template_vars,
                volumes=volumes,
                wait_services=wait_services,
                credentials={
                    "domain": variables["domain"],
                    "global_api_key": global_api_key,
                    "database_name": database_name,
                    "manager_url": f"https://{variables['domain']}/manager",
                    "api_url": f"https://{variables['domain']}",
                },
            )

            if not success:
                self.logger.error("Falha na instalação da Evolution API")
                return False

            self.logger.info("Instalação da Evolution API concluída com sucesso")
            self.logger.info(f"Manager: https://{variables['domain']}/manager")
            self.logger.info(f"API URL: https://{variables['domain']}")
            self.logger.info(f"Global API Key: {global_api_key}")
            return True

        except Exception as e:
            self.logger.error(f"Erro durante instalação da Evolution API: {e}")
            return False
