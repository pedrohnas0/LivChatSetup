#!/usr/bin/env python3

import subprocess
import logging
import secrets
import string
from .base_setup import BaseSetup

class PgVectorSetup(BaseSetup):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.pgvector_password = None

    def generate_password(self, length=16):
        """Gera uma senha aleatória segura"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def create_pgvector_stack(self):
        """Cria o arquivo docker-compose para PostgreSQL com PgVector"""
        self.logger.info("Criando stack do PostgreSQL com PgVector")
        
        # Gera senha aleatória
        self.pgvector_password = self.generate_password()
        
        stack_content = f"""version: "3.7"
services:

## --------------------------- ORION --------------------------- ##

  pgvector:
    image: pgvector/pgvector:pg16
    command: >
      postgres
      -c max_connections=500
      -c shared_buffers=512MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100

    volumes:
      - pgvector_data:/var/lib/postgresql/data

    networks:
      - orion_network

    ## Descomente as linhas abaixo para uso externo
    #ports:
    #  - 5433:5432

    environment:
      ## Senha do postgres 
      - POSTGRES_PASSWORD={self.pgvector_password}
      - POSTGRES_DB=vectordb

      ## Timezone
      - TZ=America/Sao_Paulo

    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          cpus: "2"
          memory: 2048M

## --------------------------- ORION --------------------------- ##

volumes:
  pgvector_data:
    external: true
    name: pgvector_data

networks:
  orion_network:
    external: true
    name: orion_network
"""
        
        stack_file = "/tmp/pgvector.yaml"
        try:
            with open(stack_file, 'w') as f:
                f.write(stack_content)
            self.logger.info("Stack do PgVector criada com sucesso")
            return stack_file
        except Exception as e:
            self.logger.error(f"Erro ao criar stack do PgVector: {e}")
            return None

    def create_volume(self):
        """Cria o volume para PgVector"""
        self.logger.info("Criando volume pgvector_data")
        result = self.run_command(["docker", "volume", "create", "pgvector_data"])
        if result.returncode == 0:
            self.logger.info("Volume pgvector_data criado com sucesso")
            return True
        else:
            self.logger.error("Erro ao criar volume pgvector_data")
            return False

    def deploy_stack(self, stack_file):
        """Faz deploy da stack PgVector"""
        self.logger.info("Fazendo deploy da stack PgVector")
        
        result = self.run_command([
            "docker", "stack", "deploy", 
            "--prune", "--resolve-image", "always",
            "-c", stack_file, "pgvector"
        ])
        
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
            result = self.run_command([
                "docker", "service", "ps", "pgvector_pgvector", 
                "--format", "{{.CurrentState}}"
            ])
            
            if result.returncode == 0 and "Running" in result.stdout:
                self.logger.info("PgVector está online")
                return True
                
            time.sleep(5)
        
        self.logger.error("Timeout aguardando PgVector ficar online")
        return False

    def verify_stack(self):
        """Verifica se a stack PgVector está rodando"""
        result = self.run_command(["docker", "stack", "ls", "--format", "{{.Name}}"])
        
        if result.returncode == 0:
            stacks = result.stdout.strip().split('\n')
            if 'pgvector' in stacks:
                self.logger.info("Stack do PgVector encontrada")
                return True
        
        self.logger.error("Stack do PgVector não encontrada")
        return False

    def save_credentials(self):
        """Salva as credenciais do PgVector"""
        self.logger.info("Salvando credenciais do PgVector")
        
        credentials = f"""[ POSTGRESQL + PGVECTOR ]

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
        
        try:
            # Cria diretório se não existir
            self.run_command(["mkdir", "-p", "/root/dados_vps"])
            
            with open("/root/dados_vps/dados_pgvector", 'w') as f:
                f.write(credentials)
            
            self.logger.info("Credenciais salvas em /root/dados_vps/dados_pgvector")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
            return False

    def run_pgvector_setup(self):
        """Executa a instalação completa do PgVector"""
        self.logger.info("Iniciando instalação do PostgreSQL com PgVector")
        
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
        self.logger.info("Credenciais salvas em /root/dados_vps/dados_pgvector")
        
        return True
