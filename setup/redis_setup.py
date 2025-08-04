#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine

class RedisSetup(BaseSetup):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.redis_password = None

    def generate_password(self, length=16):
        """Gera uma senha aleatória segura"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def create_redis_stack(self):
        """Cria o arquivo docker-compose para Redis usando template Jinja2"""
        self.logger.info("Criando stack do Redis")
        
        # Gera senha aleatória
        self.redis_password = self.generate_password()
        
        # Usa o template engine para renderizar o template
        template_engine = TemplateEngine()
        template_vars = {
            'redis_password': self.redis_password,
            'network_name': 'orion_network'
        }
        
        stack_file = template_engine.render_template(
            'redis.yaml.j2', 
            template_vars, 
            '/tmp/redis.yaml'
        )
        
        if stack_file:
            self.logger.info("Stack do Redis criada com sucesso")
            return stack_file
        else:
            self.logger.error("Erro ao criar stack do Redis")
            return None

    def create_volume(self):
        """Cria o volume para Redis"""
        self.logger.info("Criando volume redis_data")
        result = self.run_command(["docker", "volume", "create", "redis_data"])
        if result.returncode == 0:
            self.logger.info("Volume redis_data criado com sucesso")
            return True
        else:
            self.logger.error("Erro ao criar volume redis_data")
            return False

    def deploy_stack(self, stack_file):
        """Faz deploy da stack Redis"""
        self.logger.info("Fazendo deploy da stack Redis")
        
        result = self.run_command([
            "docker", "stack", "deploy", 
            "--prune", "--resolve-image", "always",
            "-c", stack_file, "redis"
        ])
        
        if result.returncode == 0:
            self.logger.info("Stack Redis deployada com sucesso")
            return True
        else:
            self.logger.error("Erro ao deployar stack Redis")
            return False

    def wait_for_service(self, timeout=120):
        """Aguarda o serviço Redis ficar online"""
        self.logger.info(f"Aguardando Redis ficar online (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.run_command([
                "docker", "service", "ps", "redis_redis", 
                "--format", "{{.CurrentState}}"
            ])
            
            if result.returncode == 0 and "Running" in result.stdout:
                self.logger.info("Redis está online")
                return True
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando Redis ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack Redis está rodando"""
        result = self.run_command(["docker", "stack", "ls", "--format", "{{.Name}}"])
        
        if result.returncode == 0:
            stacks = result.stdout.strip().split('\n')
            if 'redis' in stacks:
                self.logger.info("Stack do Redis encontrada")
                return True
        
        self.logger.error("Stack do Redis não encontrada")
        return False

    def save_credentials(self):
        """Salva as credenciais do Redis"""
        self.logger.info("Salvando credenciais do Redis")
        
        credentials = f"""[ REDIS ]

Dominio do Redis: redis://redis:6379

Usuario: default
Senha: {self.redis_password}

Conexão interna: redis://:${self.redis_password}@redis:6379
"""
        
        try:
            # Cria diretório se não existir
            self.run_command(["mkdir", "-p", "/root/dados_vps"])
            
            with open("/root/dados_vps/dados_redis", 'w') as f:
                f.write(credentials)
            
            self.logger.info("Credenciais salvas em /root/dados_vps/dados_redis")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run_redis_setup(self):
        """Executa a instalação completa do Redis"""
        self.logger.info("Iniciando instalação do Redis")
        
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        
        # Cria volume
        if not self.create_volume():
            return False
        
        # Cria stack
        stack_file = self.create_redis_stack()
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
        
        self.logger.info("Instalação do Redis concluída com sucesso")
        self.logger.info(f"Senha gerada: {self.redis_password}")
        self.logger.info("Credenciais salvas em /root/dados_vps/dados_redis")
        
        return True
