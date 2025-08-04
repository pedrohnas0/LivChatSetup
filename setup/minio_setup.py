#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
from .base_setup import BaseSetup

class MinioSetup(BaseSetup):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.minio_user = None
        self.minio_password = None
        self.minio_domain = None
        self.s3_domain = None

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
        """Cria o arquivo docker-compose para MinIO"""
        self.logger.info("Criando stack do MinIO")
        
        stack_content = f"""version: "3.7"
services:

## --------------------------- ORION --------------------------- ##

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"

    volumes:
      - minio_data:/data

    networks:
      - orion_network

    environment:
      - MINIO_ROOT_USER={self.minio_user}
      - MINIO_ROOT_PASSWORD={self.minio_password}
      - TZ=America/Sao_Paulo

    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          cpus: "1"
          memory: 1024M
      labels:
        - traefik.enable=true
        - traefik.swarm.network=orion_network
        
        # Console MinIO (porta 9001)
        - traefik.http.services.minio-console.loadbalancer.server.port=9001
        - traefik.http.routers.minio-console.rule=Host(`{self.minio_domain}`)
        - traefik.http.routers.minio-console.service=minio-console
        - traefik.http.routers.minio-console.entrypoints=websecure
        - traefik.http.routers.minio-console.tls.certresolver=letsencryptresolver
        
        # API S3 (porta 9000)
        - traefik.http.services.minio-s3.loadbalancer.server.port=9000
        - traefik.http.routers.minio-s3.rule=Host(`{self.s3_domain}`)
        - traefik.http.routers.minio-s3.service=minio-s3
        - traefik.http.routers.minio-s3.entrypoints=websecure
        - traefik.http.routers.minio-s3.tls.certresolver=letsencryptresolver

## --------------------------- ORION --------------------------- ##

volumes:
  minio_data:
    external: true
    name: minio_data

networks:
  orion_network:
    external: true
    name: orion_network
"""
        
        stack_file = "/tmp/minio.yaml"
        try:
            with open(stack_file, 'w') as f:
                f.write(stack_content)
            self.logger.info("Stack do MinIO criada com sucesso")
            return stack_file
        except Exception as e:
            self.logger.error(f"Erro ao criar stack do MinIO: {e}")
            return None

    def create_volume(self):
        """Cria o volume para MinIO"""
        self.logger.info("Criando volume minio_data")
        result = self.run_command(["docker", "volume", "create", "minio_data"])
        if result.returncode == 0:
            self.logger.info("Volume minio_data criado com sucesso")
            return True
        else:
            self.logger.error("Erro ao criar volume minio_data")
            return False

    def deploy_stack(self, stack_file):
        """Faz deploy da stack MinIO"""
        self.logger.info("Fazendo deploy da stack MinIO")
        
        result = self.run_command([
            "docker", "stack", "deploy", 
            "--prune", "--resolve-image", "always",
            "-c", stack_file, "minio"
        ])
        
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
            result = self.run_command([
                "docker", "service", "ps", "minio_minio", 
                "--format", "{{.CurrentState}}"
            ])
            
            if result.returncode == 0 and "Running" in result.stdout:
                self.logger.info("MinIO está online")
                return True
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando MinIO ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack MinIO está rodando"""
        result = self.run_command(["docker", "stack", "ls", "--format", "{{.Name}}"])
        
        if result.returncode == 0:
            stacks = result.stdout.strip().split('\n')
            if 'minio' in stacks:
                self.logger.info("Stack do MinIO encontrada")
                return True
        
        self.logger.error("Stack do MinIO não encontrada")
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
            self.run_command(["mkdir", "-p", "/root/dados_vps"])
            
            with open("/root/dados_vps/dados_minio", 'w') as f:
                f.write(credentials)
            
            self.logger.info("Credenciais salvas em /root/dados_vps/dados_minio")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run_minio_setup(self):
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
