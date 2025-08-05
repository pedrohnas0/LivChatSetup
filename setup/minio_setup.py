#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
import os
import time
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine
from utils.portainer_api import PortainerAPI

class MinioSetup(BaseSetup):
    def __init__(self):
        super().__init__("Instalação do MinIO")
        self.minio_user = None
        self.minio_password = None
        self.minio_domain = None
        self.s3_domain = None

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
        # MinIO requer pelo menos 8 caracteres
        alphabet = string.ascii_letters + string.digits + "@_"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def generate_username(self):
        """Gera um username aleatório"""
        return f"admin{secrets.randbelow(9999):04d}"

    def get_user_input(self):
        """Solicita informações do usuário para MinIO"""
        print("\n=== Configuração do MinIO ===")
        
        # Solicita domínio do MinIO
        while True:
            self.minio_domain = input("Digite o domínio para o MinIO (ex: minio.seudominio.com): ").strip()
            if self.minio_domain:
                break
            print("Domínio é obrigatório!")
        
        # Solicita domínio do S3
        while True:
            self.s3_domain = input("Digite o domínio para o MinIO S3 (ex: s3.seudominio.com): ").strip()
            if self.s3_domain:
                break
            print("Domínio S3 é obrigatório!")
        
        # Gera credenciais automaticamente
        self.minio_user = self.generate_username()
        self.minio_password = self.generate_password()
        
        print(f"\nCredenciais geradas automaticamente:")
        print(f"Usuário: {self.minio_user}")
        print(f"Senha: {self.minio_password}")
        
        # Confirmação
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        return confirm in ['s', 'sim', 'y', 'yes']

    def create_minio_stack(self):
        """Cria o arquivo docker-compose para MinIO usando template Jinja2"""
        self.logger.info("Criando stack do MinIO")
        
        # Usa o template engine para renderizar o template
        template_engine = TemplateEngine()
        template_vars = {
            'minio_user': self.minio_user,
            'minio_password': self.minio_password,
            'minio_domain': self.minio_domain,
            's3_domain': self.s3_domain,
            'network_name': 'orion_network'
        }
        
        # Renderiza o template
        rendered_content = template_engine.render_template(
            'docker-compose/minio.yaml.j2', 
            template_vars
        )
        
        # Salva o arquivo renderizado
        stack_file_path = '/tmp/minio.yaml'
        try:
            with open(stack_file_path, 'w') as f:
                f.write(rendered_content)
            self.logger.info("Stack do MinIO criada com sucesso")
            return stack_file_path
        except Exception as e:
            self.logger.error(f"Erro ao salvar stack do MinIO: {e}")
            return None

    def create_volume(self):
        """Cria o volume para MinIO"""
        return self.run_command(
            "docker volume create minio_data",
            "criação do volume minio_data"
        )

    def deploy_stack(self, stack_file):
        """Faz deploy da stack MinIO via API do Portainer"""
        try:
            portainer = PortainerAPI()
            success = portainer.deploy_stack("minio", stack_file)
            
            if success:
                self.logger.info("Deploy da stack MinIO realizado com sucesso via API do Portainer")
                return True
            else:
                self.logger.error("Falha no deploy da stack MinIO via API do Portainer")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no deploy da stack MinIO: {e}")
            return False
        
        if result.returncode == 0:
            self.logger.info("Stack MinIO deployada com sucesso")
            return True
        else:
            self.logger.error("Erro ao deployar stack MinIO")
            return False

    def wait_for_service(self, timeout=120):
        """Aguarda o serviço MinIO ficar online"""
        self.logger.info(f"Aguardando MinIO ficar online (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    "docker service ps minio_minio --format '{{.CurrentState}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and "Running" in result.stdout:
                    self.logger.info("MinIO está online")
                    return True
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("Timeout ao verificar status do MinIO")
            except Exception as e:
                self.logger.warning(f"Erro ao verificar status do MinIO: {e}")
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando MinIO ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack MinIO está rodando"""
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
                if 'minio' in stacks:
                    self.logger.info("Stack do MinIO encontrada")
                    return True
            
            self.logger.error("Stack do MinIO não encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar stack MinIO: {e}")
            return False

    def save_credentials(self):
        """Salva as credenciais do MinIO"""
        self.logger.info("Salvando credenciais do MinIO")
        
        credentials = f"""[ MINIO ]

Console MinIO: https://{self.minio_domain}
API S3: https://{self.s3_domain}

Usuario: {self.minio_user}
Senha: {self.minio_password}

Endpoint S3: https://{self.s3_domain}
Access Key: {self.minio_user}
Secret Key: {self.minio_password}
Region: us-east-1

Exemplo de configuração AWS CLI:
aws configure set aws_access_key_id {self.minio_user}
aws configure set aws_secret_access_key {self.minio_password}
aws configure set default.region us-east-1
aws configure set default.s3.signature_version s3v4
aws configure set default.s3.addressing_style path
"""
        
        try:
            # Cria diretório se não existir
            os.makedirs("/root/dados_vps", exist_ok=True)
            
            with open("/root/dados_vps/dados_minio", 'w') as f:
                f.write(credentials)
            
            self.logger.info("Credenciais salvas em /root/dados_vps/dados_minio")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run(self):
        """Executa a instalação completa do MinIO"""
        self.logger.info("Iniciando instalação do MinIO")
        
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        
        # Solicita informações do usuário
        if not self.get_user_input():
            self.logger.info("Instalação cancelada pelo usuário")
            return False
        
        # Cria volume
        if not self.create_volume():
            return False
        
        # Cria stack
        stack_file = self.create_minio_stack()
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
        
        self.logger.info("Instalação do MinIO concluída com sucesso")
        self.logger.info(f"Console: https://{self.minio_domain}")
        self.logger.info(f"API S3: https://{self.s3_domain}")
        self.logger.info(f"Usuário: {self.minio_user}")
        self.logger.info("Credenciais salvas em /root/dados_vps/dados_minio")
        
        return True
