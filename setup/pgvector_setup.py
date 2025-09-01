#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
import os
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine
from utils.portainer_api import PortainerAPI
from utils.config_manager import ConfigManager
from datetime import datetime

class PgVectorSetup(BaseSetup):
    def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do PostgreSQL com PgVector")
        self.config = config_manager or ConfigManager()
        self.pgvector_password = None
        self.network_name = network_name

    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Verifica se Docker está instalado
        if not self.is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
            
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
            
        return True

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

    def is_swarm_active(self) -> bool:
        """Verifica se Docker Swarm está ativo"""
        try:
            result = subprocess.run(
                "docker info --format '{{.Swarm.LocalNodeState}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and result.stdout.strip() == 'active'
        except Exception as e:
            self.logger.debug(f"Erro ao verificar Swarm: {e}")
            return False

    def generate_password(self, length=16):
        """Gera uma senha aleatória segura"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def create_pgvector_stack(self):
        """Cria o arquivo docker-compose para PostgreSQL com PgVector usando template Jinja2"""
        self.logger.info("Criando stack do PostgreSQL com PgVector")
        
        # Gera senha aleatória
        self.pgvector_password = self.generate_password()
        
        # Usa o template engine para renderizar o template
        template_engine = TemplateEngine()
        template_vars = {
            'pgvector_password': self.pgvector_password,
            'network_name': self.network_name
        }
        
        # Renderiza o template
        rendered_content = template_engine.render_template(
            'docker-compose/pgvector.yaml.j2', 
            template_vars
        )
        
        # Salva o arquivo renderizado
        stack_file_path = '/tmp/pgvector.yaml'
        try:
            with open(stack_file_path, 'w') as f:
                f.write(rendered_content)
            self.logger.info("Stack do PostgreSQL com PgVector criada com sucesso")
            return stack_file_path
        except Exception as e:
            self.logger.error(f"Erro ao salvar stack do PostgreSQL com PgVector: {e}")
            return None

    def create_volume(self):
        """Cria o volume para PostgreSQL com PgVector"""
        return self.run_command(
            "docker volume create pgvector_data",
            "criação do volume pgvector_data"
        )

    def deploy_stack(self, stack_file):
        """Faz deploy da stack PgVector via API do Portainer"""
        try:
            portainer = PortainerAPI()
            success = portainer.deploy_stack("pgvector", stack_file)
            
            if success:
                self.logger.info("Deploy da stack PgVector realizado com sucesso via API do Portainer")
                return True
            else:
                self.logger.error("Falha no deploy da stack PgVector via API do Portainer")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no deploy da stack PgVector: {e}")
            return False
        
        if result.returncode == 0:
            self.logger.info("Stack PgVector deployada com sucesso")
            return True
        else:
            self.logger.error("Erro ao deployar stack PgVector")
            return False

    def wait_for_service(self, timeout=120):
        """Aguarda o serviço PgVector ficar online"""
        self.logger.info(f"Aguardando PgVector ficar online (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    "docker service ps pgvector_pgvector --format '{{.CurrentState}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and "Running" in result.stdout:
                    self.logger.info("PgVector está online")
                    return True
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Timeout ao verificar status do PgVector")
            except Exception as e:
                self.logger.warning(f"Erro ao verificar status do PgVector: {e}")
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando PgVector ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack PgVector está rodando"""
        try:
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                stacks = result.stdout.strip().split('\n')
                if 'pgvector' in stacks:
                    self.logger.info("Stack do PgVector encontrada")
                    return True
            
            self.logger.error("Stack do PgVector não encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar stack PgVector: {e}")
            return False

    def _is_pgvector_running(self) -> bool:
        """Verifica se o PgVector já está rodando"""
        try:
            # Verifica se a stack existe
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and 'pgvector' in result.stdout:
                # Verifica se o serviço está rodando
                service_result = subprocess.run(
                    "docker service ps pgvector_pgvector --format '{{.CurrentState}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if service_result.returncode == 0 and "Running" in service_result.stdout:
                    self.logger.info("PgVector já está rodando")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Erro ao verificar PgVector: {e}")
            return False
    
    def save_credentials(self):
        """Salva as credenciais do PgVector"""
        self.logger.info("Salvando credenciais do PgVector")
        
        # Salva no ConfigManager (novo método)
        credentials_data = {
            'password': self.pgvector_password,
            'host': 'pgvector',
            'port': '5432',
            'database': 'vectordb',
            'username': 'postgres',
            'connection_string': f'postgresql://postgres:{self.pgvector_password}@pgvector:5432/vectordb'
        }
        
        try:
            # Salva no ConfigManager
            self.config.save_app_credentials('pgvector', credentials_data)
            self.config.save_app_config('pgvector', {
                'host': 'pgvector',
                'port': 5432,
                'database': 'vectordb',
                'extensions': ['vector'],
                'configured_at': datetime.now().isoformat()
            })
            self.logger.info("Credenciais salvas no ConfigManager")
            
            # Mantém arquivo legado para compatibilidade temporária
            # TODO: Remover após migração completa de todos os módulos
            credentials_legacy = f"""[ POSTGRESQL + PGVECTOR ]

Host: pgvector
Port: 5432
Database: vectordb
Usuario: postgres
Senha: {self.pgvector_password}

String de conexão: postgresql://postgres:{self.pgvector_password}@pgvector:5432/vectordb

Extensões disponíveis:
- vector (para embeddings e busca semântica)
- Suporte a índices HNSW e IVFFlat

Exemplo de uso:
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE embeddings (id bigserial PRIMARY KEY, embedding vector(1536));
"""
            
            # Cria diretório se não existir
            os.makedirs("/root/dados_vps", exist_ok=True)
            
            with open("/root/dados_vps/dados_pgvector", 'w') as f:
                f.write(credentials_legacy)
            
            self.logger.info("Arquivo legado mantido em /root/dados_vps/dados_pgvector para compatibilidade")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run(self):
        """Executa a instalação completa do PgVector"""
        self.logger.info("Iniciando instalação do PostgreSQL com PgVector")
        
        # Verifica se já está instalado e rodando
        if self._is_pgvector_running():
            # Verifica se as credenciais existem no ConfigManager
            existing_creds = self.config.get_app_credentials('pgvector')
            if existing_creds and existing_creds.get('password'):
                self.logger.info("PgVector já está rodando e configurado, pulando instalação")
                self.pgvector_password = existing_creds['password']
                return True
        
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        
        # Cria volume
        if not self.create_volume():
            return False
        
        # Cria stack
        stack_file = self.create_pgvector_stack()
        if not stack_file:
            return False
        
        # Deploy da stack
        if not self.deploy_stack(stack_file):
            return False
        
        # Aguarda serviço ficar online
        if not self.wait_for_service():
            return False
        
        # Verifica stack
        if not self.verify_stack():
            return False
        
        # Salva credenciais
        if not self.save_credentials():
            return False
        
        self.logger.info("Instalação do PgVector concluída com sucesso")
        self.logger.info(f"Senha gerada: {self.pgvector_password}")
        self.logger.info("Credenciais salvas no ConfigManager e arquivo legado para compatibilidade")
        
        return True
