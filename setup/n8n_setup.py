#!/usr/bin/env python3
"""
Módulo de setup do N8N
Baseado na função ferramenta_n8n() do SetupOrionOriginal.sh
Inclui integração com Cloudflare para DNS automático
"""

import os
import secrets
import subprocess
from setup.base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.template_engine import TemplateEngine
from utils.cloudflare_api import get_cloudflare_api

class N8NSetup(BaseSetup):
    """Setup do N8N com integração Cloudflare"""
    
    def __init__(self):
        super().__init__("n8n")
        self.service_name = "n8n"
        self.portainer_api = PortainerAPI()
        self.template_engine = TemplateEngine()
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para o N8N"""
        # Verifica se PostgreSQL está rodando
        try:
            result = subprocess.run(
                "docker ps --filter 'name=postgres' --format '{{.Names}}'",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                self.logger.error("❌ PostgreSQL não encontrado. Execute primeiro o módulo PostgreSQL.")
                return False
            
            # Verifica se Redis está rodando
            result = subprocess.run(
                "docker ps --filter 'name=redis' --format '{{.Names}}'",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                self.logger.error("❌ Redis não encontrado. Execute primeiro o módulo Redis.")
                return False
            
            self.logger.info("✅ Pré-requisitos validados")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao validar pré-requisitos: {e}")
            return False
    
    def run(self) -> bool:
        """Executa o setup do N8N"""
        if not self.validate_prerequisites():
            return False
        
        return self.install()
        
    def collect_user_inputs(self):
        """Coleta informações do usuário para o N8N"""
        self.logger.info("=== Configuração do N8N ===")
        
        # Domínio do N8N Editor
        while True:
            n8n_domain = input("Digite o domínio para o N8N Editor (ex: edt.dev.livchat.ai): ").strip()
            if n8n_domain:
                break
            print("❌ Domínio é obrigatório!")
        
        # Domínio do Webhook
        while True:
            webhook_domain = input("Digite o domínio para o Webhook do N8N (ex: whk.dev.livchat.ai): ").strip()
            if webhook_domain:
                break
            print("❌ Domínio do webhook é obrigatório!")
        
        # Configurações SMTP
        smtp_email = input("Digite o Email para SMTP (ex: contato@livchat.ai): ").strip()
        smtp_user = input("Digite o Usuário para SMTP (ex: contato@livchat.ai): ").strip()
        smtp_password = input("Digite a Senha SMTP do Email: ").strip()
        smtp_host = input("Digite o Host SMTP do Email (ex: smtp.hostinger.com): ").strip()
        
        while True:
            try:
                smtp_port = int(input("Digite a porta SMTP do Email (ex: 465): ").strip())
                break
            except ValueError:
                print("❌ Porta deve ser um número!")
        
        # Define SSL baseado na porta
        smtp_secure = "true" if smtp_port == 465 else "false"
        
        # Confirmação
        print(f"\n=== Configuração do N8N ===")
        print(f"Domínio N8N: {n8n_domain}")
        print(f"Domínio Webhook: {webhook_domain}")
        print(f"Email SMTP: {smtp_email}")
        print(f"Usuário SMTP: {smtp_user}")
        print(f"Host SMTP: {smtp_host}")
        print(f"Porta SMTP: {smtp_port}")
        print(f"SSL SMTP: {smtp_secure}")
        
        confirm = input("\nConfirma as configurações? (s/N): ").strip().lower()
        if confirm != 's':
            print("❌ Configuração cancelada pelo usuário")
            return None
            
        return {
            'n8n_domain': n8n_domain,
            'webhook_domain': webhook_domain,
            'smtp_email': smtp_email,
            'smtp_user': smtp_user,
            'smtp_password': smtp_password,
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_secure': smtp_secure
        }
    
    def setup_dns_records(self, n8n_domain, webhook_domain):
        """Configura registros DNS via Cloudflare"""
        self.logger.info("Configurando registros DNS via Cloudflare...")
        
        # Obtém instância da Cloudflare API
        cf = get_cloudflare_api(self.logger)
        if not cf:
            self.logger.error("Falha ao inicializar Cloudflare API")
            return False
        
        # Configura DNS para o serviço N8N
        domains = [n8n_domain, webhook_domain]
        return cf.setup_dns_for_service("N8N", domains)
    
    def get_postgres_password(self):
        """Obtém a senha do PostgreSQL (N8N usa PostgreSQL, não PgVector)"""
        try:
            with open('/root/dados_vps/dados_postgres', 'r') as f:
                for line in f:
                    if line.startswith('Senha:'):
                        return line.split(':', 1)[1].strip()
            self.logger.error("Senha não encontrada no arquivo dados_postgres")
            return None
        except FileNotFoundError:
            self.logger.error("Arquivo de credenciais do PostgreSQL não encontrado")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do PostgreSQL: {e}")
            return None
    
    def get_redis_password(self):
        """Obtém a senha do Redis"""
        try:
            with open('/root/dados_vps/dados_redis', 'r') as f:
                for line in f:
                    if line.startswith('Senha:'):
                        return line.split(':', 1)[1].strip()
            self.logger.error("Senha não encontrada no arquivo dados_redis")
            return None
        except FileNotFoundError:
            self.logger.error("Arquivo de credenciais do Redis não encontrado")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao obter senha do Redis: {e}")
            return None
    
    def create_database(self, database_name):
        """Cria banco de dados no PostgreSQL"""
        postgres_password = self.get_postgres_password()
        if not postgres_password:
            return False
        
        try:
            # Encontra container do PostgreSQL
            result = subprocess.run(
                "docker ps --filter 'name=postgres' --format '{{.Names}}'",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                self.logger.error("Container PostgreSQL não encontrado")
                return False
            
            container_name = result.stdout.strip().split('\n')[0]
            
            # Verifica se banco de dados existe
            check_db_cmd = f"docker exec {container_name} psql -U postgres -t -c \"SELECT 1 FROM pg_database WHERE datname = '{database_name}';\""
            
            result = subprocess.run(check_db_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
            
            if result.stdout.strip():
                self.logger.info(f"✅ Banco de dados '{database_name}' já existe")
                return True
            
            # Cria o banco se não existir
            create_db_cmd = f"docker exec {container_name} psql -U postgres -c \"CREATE DATABASE {database_name};\""
            
            self.logger.info(f"🔧 Criando banco de dados '{database_name}'...")
            
            result = subprocess.run(create_db_cmd, shell=True, capture_output=True, text=True, env={'PGPASSWORD': postgres_password})
            
            if result.returncode == 0:
                self.logger.info(f"✅ Banco de dados '{database_name}' criado/verificado")
                return True
            else:
                self.logger.error(f"Erro ao criar banco: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao criar banco de dados: {e}")
            return False
    
    def install(self):
        """Instala o N8N"""
        try:
            # Coleta dados do usuário
            user_data = self.collect_user_inputs()
            if not user_data:
                return False
            
            self.logger.info("Iniciando instalação do N8N...")
            
            # Configura DNS via Cloudflare
            if not self.setup_dns_records(user_data['n8n_domain'], user_data['webhook_domain']):
                self.logger.warning("Falha na configuração DNS, mas continuando...")
            
            # Verifica/cria banco de dados
            database_name = "n8n_queue"
            if not self.create_database(database_name):
                self.logger.error("Falha ao criar banco de dados")
                return False
            
            # Obtém senha do PostgreSQL
            postgres_password = self.get_postgres_password()
            if not postgres_password:
                self.logger.error("Falha ao obter senha do PostgreSQL")
                return False
            
            # Obtém senha do Redis
            redis_password = self.get_redis_password()
            if not redis_password:
                self.logger.error("Falha ao obter senha do Redis")
                return False
            
            # Gera chave de criptografia
            encryption_key = secrets.token_hex(16)
            
            # Prepara variáveis para o template
            variables = {
                'network_name': 'orion_network',
                'database_name': database_name,
                'postgres_password': postgres_password,
                'redis_password': redis_password,
                'encryption_key': encryption_key,
                'n8n_domain': user_data['n8n_domain'],
                'webhook_domain': user_data['webhook_domain'],
                'smtp_email': user_data['smtp_email'],
                'smtp_user': user_data['smtp_user'],
                'smtp_password': user_data['smtp_password'],
                'smtp_host': user_data['smtp_host'],
                'smtp_port': user_data['smtp_port'],
                'smtp_secure': user_data['smtp_secure']
            }
            
            # Deploy via Portainer
            services_to_wait = ['n8n_n8n_editor', 'n8n_n8n_webhook', 'n8n_n8n_worker']
            
            success = self.portainer_api.deploy_service_complete(
                service_name="n8n",
                template_path="docker-compose/n8n.yaml.j2",
                template_vars=variables,
                wait_services=services_to_wait,
                credentials={
                    'n8n_domain': user_data['n8n_domain'],
                    'webhook_domain': user_data['webhook_domain'],
                    'encryption_key': encryption_key,
                    'database_name': database_name,
                    'smtp_email': user_data['smtp_email'],
                    'smtp_host': user_data['smtp_host'],
                    'smtp_port': user_data['smtp_port']
                }
            )
            
            if success:
                # Salva credenciais como string diretamente no arquivo
                credentials_text = f"""N8N Instalado com Sucesso!

Domínio N8N: https://{user_data['n8n_domain']}
Domínio Webhook: https://{user_data['webhook_domain']}
Chave de Criptografia: {encryption_key}
Banco de Dados: {database_name}

Configurações SMTP:
- Email: {user_data['smtp_email']}
- Host: {user_data['smtp_host']}
- Porta: {user_data['smtp_port']}
- SSL: {user_data['smtp_secure']}
"""
                
                # Salva credenciais diretamente no arquivo
                try:
                    import os
                    os.makedirs("/root/dados_vps", exist_ok=True)
                    with open("/root/dados_vps/dados_n8n", 'w', encoding='utf-8') as f:
                        f.write(credentials_text)
                    self.logger.info("Credenciais salvas em /root/dados_vps/dados_n8n")
                except Exception as e:
                    self.logger.error(f"Erro ao salvar credenciais: {e}")
                
                self.logger.info("Instalação do N8N concluída com sucesso")
                self.logger.info(f"Acesse: https://{user_data['n8n_domain']}")
                self.logger.info(f"Webhook: https://{user_data['webhook_domain']}")
                return True
            else:
                self.logger.error("Falha na instalação do N8N")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante instalação do N8N: {e}")
            return False
