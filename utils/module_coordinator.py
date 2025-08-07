#!/usr/bin/env python3
"""
Coordenador de Módulos
Simplifica a execução e gerenciamento dos módulos de setup
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import setup_logging
from setup.basic_setup import SystemSetup as BasicSetup
from setup.hostname_setup import HostnameSetup
from setup.docker_setup import DockerSetup
from setup.traefik_setup import TraefikSetup
from setup.portainer_setup import PortainerSetup
from setup.cleanup_setup import CleanupSetup
from setup.redis_setup import RedisSetup
from setup.postgres_setup import PostgresSetup
from setup.pgvector_setup import PgVectorSetup
from setup.minio_setup import MinioSetup
from setup.chatwoot_setup import ChatwootSetup
from setup.n8n_setup import N8NSetup
from setup.grafana_setup import GrafanaSetup
from setup.gowa_setup import GowaSetup

class ModuleCoordinator:
    """Coordenador simplificado dos módulos de setup"""
    
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging()
        self.start_time = datetime.now()
        
    def get_user_input(self, prompt: str, required: bool = False) -> str:
        """Coleta entrada do usuário de forma interativa"""
        try:
            value = input(f"{prompt}: ").strip()
            if required and not value:
                self.logger.warning("Valor obrigatório não fornecido")
                return None
            return value if value else None
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return None
    
    def execute_module_instance(self, module_name: str, module_instance) -> bool:
        """Executa uma instância de módulo específico"""
        self.logger.info(f"Iniciando módulo: {module_name}")
        
        try:
            success = module_instance.run()
            if success:
                self.logger.info(f"Módulo {module_name} concluído com sucesso")
            else:
                self.logger.error(f"Módulo {module_name} falhou")
            return success
        except Exception as e:
            self.logger.error(f"Exceção no módulo {module_name}: {e}")
            return False
    
    def execute_module(self, module_name, **kwargs):
        """Executa um módulo específico por nome"""
        try:
            if module_name == 'basic':
                basic_setup = BasicSetup()
                return basic_setup.run_basic_setup()
            
            elif module_name == 'hostname':
                # Hostname será solicitado pelo próprio módulo se não fornecido
                hostname_setup = HostnameSetup(kwargs.get('hostname') or self.args.hostname)
                return hostname_setup.run()
            
            elif module_name == 'docker':
                docker_setup = DockerSetup()
                return docker_setup.run()
            
            elif module_name == 'traefik':
                # Email será solicitado pelo próprio módulo se não fornecido
                traefik_setup = TraefikSetup(kwargs.get('email') or self.args.email)
                return traefik_setup.run()
            
            elif module_name == 'portainer':
                # Domínio será solicitado pelo próprio módulo se não fornecido
                portainer_setup = PortainerSetup(kwargs.get('portainer_domain') or self.args.portainer_domain)
                return portainer_setup.run()
            
            elif module_name == 'redis':
                redis_setup = RedisSetup()
                return redis_setup.run()
            
            elif module_name == 'postgres':
                postgres_setup = PostgresSetup()
                return postgres_setup.run()
            
            elif module_name == 'pgvector':
                pgvector_setup = PgVectorSetup()
                return pgvector_setup.run()
            
            elif module_name == 'minio':
                # MinIO já solicita domínios internamente
                minio_setup = MinioSetup()
                return minio_setup.run()
            
            elif module_name == 'chatwoot':
                chatwoot_setup = ChatwootSetup()
                return chatwoot_setup.run()
            
            elif module_name == 'n8n':
                n8n_setup = N8NSetup()
                return n8n_setup.install()
            
            elif module_name == 'grafana':
                grafana_setup = GrafanaSetup()
                return grafana_setup.run()
            
            elif module_name == 'gowa':
                gowa_setup = GowaSetup()
                return gowa_setup.run()
            
            elif module_name == 'cleanup':
                cleanup_setup = CleanupSetup()
                return cleanup_setup.run()
            
            else:
                self.logger.error(f"Módulo '{module_name}' não encontrado")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao executar módulo {module_name}: {e}")
            return False
    
    def run_basic_setup(self) -> bool:
        """Executa setup básico"""
        basic_setup = BasicSetup()
        return basic_setup.run_basic_setup()
    
    def run_hostname_setup(self, hostname: str) -> bool:
        """Executa configuração de hostname"""
        if not hostname:
            return True  # Skip se não fornecido
        hostname_setup = HostnameSetup(hostname)
        return self.execute_module_instance("Hostname", hostname_setup)
    
    def run_docker_setup(self) -> bool:
        """Executa instalação do Docker"""
        docker_setup = DockerSetup(not self.args.no_swarm)
        return self.execute_module_instance("Docker", docker_setup)
    
    def run_traefik_setup(self, email: str) -> bool:
        """Executa instalação do Traefik"""
        if not email:
            # Pergunta email interativamente
            print("\n--- Configuração de SSL/Traefik ---")
            email = self.get_user_input("Digite o email para certificados SSL (Enter para pular)")
            if not email:
                self.logger.warning("Email não fornecido, pulando instalação do Traefik")
                return True
            self.logger.info(f"Email configurado: {email}")
        
        traefik_setup = TraefikSetup()
        return traefik_setup.run_traefik_setup(email)
    
    def run_portainer_setup(self, domain: str) -> bool:
        """Executa instalação do Portainer"""
        if not domain:
            # Pergunta domínio interativamente
            print("\n--- Configuração do Portainer ---")
            domain = self.get_user_input("Digite o domínio do Portainer (ex: portainer.seudominio.com, Enter para pular)")
            if not domain:
                self.logger.warning("Domínio não fornecido, pulando instalação do Portainer")
                return True
            self.logger.info(f"Domínio Portainer configurado: {domain}")
        
        portainer_setup = PortainerSetup()
        return portainer_setup.run_portainer_setup(domain)
    
    def run_redis_setup(self) -> bool:
        """Executa instalação do Redis"""
        redis_setup = RedisSetup()
        return redis_setup.run()
    
    def run_postgres_setup(self) -> bool:
        """Executa instalação do PostgreSQL"""
        postgres_setup = PostgresSetup()
        return postgres_setup.run()
    
    def run_pgvector_setup(self) -> bool:
        """Executa instalação do PostgreSQL + PgVector"""
        pgvector_setup = PgVectorSetup()
        return pgvector_setup.run()
    
    def run_minio_setup(self) -> bool:
        """Executa instalação do MinIO (S3)"""
        minio_setup = MinioSetup()
        return minio_setup.run()
    
    def run_chatwoot_setup(self) -> bool:
        """Executa setup do Chatwoot"""
        chatwoot_setup = ChatwootSetup()
        return chatwoot_setup.run()
    
    def run_cleanup_setup(self) -> bool:
        """Executa limpeza completa"""
        # Confirmação de segurança
        try:
            print("\n--- ATENÇÃO: LIMPEZA COMPLETA ---")
            print("Esta operação irá remover:")
            print("• Todas as stacks do Docker Swarm")
            print("• Volumes do projeto (vol_certificates, portainer_data)")
            print("• Redes do projeto (orion_network)")
            print("• Sair do Docker Swarm")
            print("• Limpar containers e imagens não utilizadas")
            
            confirm = input("\nDeseja continuar? (digite 'CONFIRMO' para prosseguir): ").strip()
            if confirm != "CONFIRMO":
                self.logger.info("Limpeza cancelada pelo usuário")
                return True
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return True
        
        cleanup_setup = CleanupSetup()
        return cleanup_setup.run_cleanup_setup()
    
    def get_module_map(self) -> dict:
        """Retorna mapeamento de módulos disponíveis"""
        return {
            'basic': ('Setup Básico', lambda: self.run_basic_setup()),
            'hostname': ('Hostname', lambda: self.run_hostname_setup(self.args.hostname)),
            'docker': ('Docker', lambda: self.run_docker_setup()),
            'traefik': ('Traefik', lambda: self.run_traefik_setup(self.args.email)),
            'portainer': ('Portainer', lambda: self.run_portainer_setup(self.args.portainer_domain)),
            'redis': ('Redis', lambda: self.run_redis_setup()),
            'postgres': ('PostgreSQL', lambda: self.run_postgres_setup()),
            'pgvector': ('PostgreSQL + PgVector', lambda: self.run_pgvector_setup()),
            'minio': ('MinIO (S3)', lambda: self.run_minio_setup()),
            'chatwoot': ('Chatwoot', lambda: self.run_chatwoot_setup()),
            'cleanup': ('Limpeza', lambda: self.run_cleanup_setup())
        }
    
    def run_modules(self) -> bool:
        """Executa módulos baseado nos argumentos"""
        module_map = self.get_module_map()
        failed_modules = []
        
        if self.args.module:
            # Executa módulo específico
            if self.args.module in module_map:
                module_name, module_func = module_map[self.args.module]
                success = module_func()
                if not success:
                    failed_modules.append(module_name)
            else:
                self.logger.error(f"Módulo desconhecido: {self.args.module}")
                return False
        else:
            # Executa módulos principais (exceto cleanup)
            main_modules = ['basic', 'hostname', 'docker', 'traefik', 'portainer', 'redis', 'postgres', 'pgvector', 'minio']
            
            for module_key in main_modules:
                if module_key in module_map:
                    module_name, module_func = module_map[module_key]
                    success = module_func()
                    if not success:
                        failed_modules.append(module_name)
                        if self.args.stop_on_error:
                            self.logger.error(f"Parando execução devido a falha em: {module_name}")
                            break
        
        return len(failed_modules) == 0
    
    def show_summary(self, success: bool) -> None:
        """Exibe resumo da execução"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if success:
            self.logger.info(f"Setup concluído com sucesso ({duration:.2f}s)")
            self.logger.info("Próximas etapas: Portainer, Traefik, aplicações")
        else:
            self.logger.error(f"Setup concluído com falhas ({duration:.2f}s)")
