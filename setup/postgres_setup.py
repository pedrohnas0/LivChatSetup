#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine

class PostgresSetup(BaseSetup):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.postgres_password = None

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
            'network_name': 'orion_network'
        }
        
        stack_file = template_engine.render_template(
            'postgres.yaml.j2', 
            template_vars, 
            '/tmp/postgres.yaml'
        )
        
        if stack_file:
            self.logger.info("Stack do PostgreSQL criada com sucesso")
            return stack_file
        else:
            self.logger.error("Erro ao criar stack do PostgreSQL")
            return None

    def create_volume(self):
        """Cria o volume para PostgreSQL"""
        self.logger.info("Criando volume postgres_data")
        result = self.run_command(["docker", "volume", "create", "postgres_data"])
        if result.returncode == 0:
            self.logger.info("Volume postgres_data criado com sucesso")
            return True
        else:
            self.logger.error("Erro ao criar volume postgres_data")
            return False

    def deploy_stack(self, stack_file):
        """Faz deploy da stack PostgreSQL"""
        self.logger.info("Fazendo deploy da stack PostgreSQL")
        
        result = self.run_command([
            "docker", "stack", "deploy", 
            "--prune", "--resolve-image", "always",
            "-c", stack_file, "postgres"
        ])
        
        if result.returncode == 0:
            self.logger.info("Stack PostgreSQL deployada com sucesso")
            return True
        else:
            self.logger.error("Erro ao deployar stack PostgreSQL")
            return False

    def wait_for_service(self, timeout=120):
        """Aguarda o serviço PostgreSQL ficar online"""
        self.logger.info(f"Aguardando PostgreSQL ficar online (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.run_command([
                "docker", "service", "ps", "postgres_postgres", 
                "--format", "{{.CurrentState}}"
            ])
            
            if result.returncode == 0 and "Running" in result.stdout:
                self.logger.info("PostgreSQL está online")
                return True
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando PostgreSQL ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack PostgreSQL está rodando"""
        result = self.run_command(["docker", "stack", "ls", "--format", "{{.Name}}"])
        
        if result.returncode == 0:
            stacks = result.stdout.strip().split('\n')
            if 'postgres' in stacks:
                self.logger.info("Stack do PostgreSQL encontrada")
                return True
        
        self.logger.error("Stack do PostgreSQL não encontrada")
        return False

    def save_credentials(self):
        """Salva as credenciais do PostgreSQL"""
        self.logger.info("Salvando credenciais do PostgreSQL")
        
        credentials = f"""[ POSTGRESQL ]

Host: postgres
Port: 5432
Database: postgres
Usuario: postgres
Senha: {self.postgres_password}

String de conexão: postgresql://postgres:{self.postgres_password}@postgres:5432/postgres
"""
        
        try:
            # Cria diretório se não existir
            self.run_command(["mkdir", "-p", "/root/dados_vps"])
            
            with open("/root/dados_vps/dados_postgres", 'w') as f:
                f.write(credentials)
            
            self.logger.info("Credenciais salvas em /root/dados_vps/dados_postgres")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run_postgres_setup(self):
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
        self.logger.info("Credenciais salvas em /root/dados_vps/dados_postgres")
        
        return True
