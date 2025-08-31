#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
import os
from datetime import datetime
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine
from utils.portainer_api import PortainerAPI
from utils.config_manager import ConfigManager

class PostgresSetup(BaseSetup):
    def __init__(self, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do PostgreSQL")
        self.postgres_password = None
        self.network_name = network_name
        self.config = config_manager or ConfigManager()

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

    def create_postgres_stack(self):
        """Cria o arquivo docker-compose para PostgreSQL usando template Jinja2"""
        self.logger.info("Criando stack do PostgreSQL")
        
        # Gera senha aleatória
        self.postgres_password = self.generate_password()
        
        # Usa o template engine para renderizar o template
        template_engine = TemplateEngine()
        template_vars = {
            'postgres_password': self.postgres_password,
            'network_name': self.network_name
        }
        
        # Renderiza o template
        rendered_content = template_engine.render_template(
            'docker-compose/postgres.yaml.j2', 
            template_vars
        )
        
        # Salva o arquivo renderizado
        stack_file_path = '/tmp/postgres.yaml'
        try:
            with open(stack_file_path, 'w') as f:
                f.write(rendered_content)
            self.logger.info("Stack do PostgreSQL criada com sucesso")
            return stack_file_path
        except Exception as e:
            self.logger.error(f"Erro ao salvar stack do PostgreSQL: {e}")
            return None

    def create_volume(self):
        """Cria o volume para PostgreSQL"""
        return self.run_command(
            "docker volume create postgres_data",
            "criação do volume postgres_data"
        )

    def deploy_stack(self, stack_file):
        """Faz deploy da stack PostgreSQL via API do Portainer"""
        try:
            portainer = PortainerAPI()
            success = portainer.deploy_stack("postgres", stack_file)
            
            if success:
                self.logger.info("Deploy da stack PostgreSQL realizado com sucesso via API do Portainer")
                return True
            else:
                self.logger.error("Falha no deploy da stack PostgreSQL via API do Portainer")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no deploy da stack PostgreSQL: {e}")
            return False

    def wait_for_service(self, timeout=120):
        """Aguarda o serviço PostgreSQL ficar online"""
        self.logger.info(f"Aguardando PostgreSQL ficar online (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    "docker service ps postgres_postgres --format '{{.CurrentState}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and "Running" in result.stdout:
                    self.logger.info("PostgreSQL está online")
                    return True
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Timeout ao verificar status do PostgreSQL")
            except Exception as e:
                self.logger.warning(f"Erro ao verificar status do PostgreSQL: {e}")
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando PostgreSQL ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack PostgreSQL está rodando"""
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
                if 'postgres' in stacks:
                    self.logger.info("Stack do PostgreSQL encontrada")
                    return True
            
            self.logger.error("Stack do PostgreSQL não encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar stack PostgreSQL: {e}")
            return False

    def save_credentials(self):
        """Salva as credenciais do PostgreSQL"""
        self.logger.info("Salvando credenciais do PostgreSQL")
        
        # Salva configuração do PostgreSQL no ConfigManager
        config_data = {
            'host': 'postgres',
            'port': 5432,
            'database': 'postgres',
            'configured_at': datetime.now().isoformat()
        }
        self.config.save_app_config('postgres', config_data)
        
        # Salva credenciais do PostgreSQL no ConfigManager
        credentials_data = {
            'host': 'postgres',
            'port': 5432,
            'database': 'postgres',
            'username': 'postgres',
            'password': self.postgres_password,
            'connection_string': f'postgresql://postgres:{self.postgres_password}@postgres:5432/postgres',
            'created_at': datetime.now().isoformat()
        }
        self.config.save_app_credentials('postgres', credentials_data)
        
        self.logger.info("Credenciais do PostgreSQL salvas no ConfigManager")
        return True

    def run(self):
        """Executa a instalação completa do PostgreSQL"""
        self.logger.info("Iniciando instalação do PostgreSQL")
        
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        
        # Cria volume
        if not self.create_volume():
            return False
        
        # Cria stack
        stack_file = self.create_postgres_stack()
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
        
        self.logger.info("Instalação do PostgreSQL concluída com sucesso")
        self.logger.info(f"Senha gerada: {self.postgres_password}")
        self.logger.info("Credenciais salvas no ConfigManager centralizado")
        
        return True
