#!/usr/bin/env python3
"""
Módulo de setup do LivChatBridge
Webhook connector entre Chatwoot e GOWA com integração PostgreSQL
Repositório: https://github.com/pedrohnas0/LivChatBridge
"""

import os
import logging
import secrets
from setup.base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.template_engine import TemplateEngine
from utils.cloudflare_api import get_cloudflare_api

class LivChatBridgeSetup(BaseSetup):
    """Setup do LivChatBridge com integração Cloudflare"""
    
    def __init__(self, network_name: str = None):
        super().__init__("livchatbridge")
        self.service_name = "livchatbridge"
        self.portainer_api = PortainerAPI()
        self.template_engine = TemplateEngine()
        self.config = {}
        self.network_name = network_name
        
        # Configurar logging para ser menos verboso
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        # Cores para output (seguindo padrão do LivChatSetup)
        self.colors = type('Colors', (), {
            'AMARELO': "\033[33m",
            'VERDE': "\033[32m", 
            'BRANCO': "\033[97m",
            'BEGE': "\033[93m",
            'VERMELHO': "\033[91m",
            'RESET': "\033[0m"
        })()
    
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
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para o LivChatBridge"""
        self.logger.info("🔍 Validando pré-requisitos do LivChatBridge...")
        
        # Verifica se Chatwoot e PostgreSQL estão disponíveis
        try:
            import subprocess
            
            # Verifica Docker
            result = subprocess.run("docker --version", shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("❌ Docker não está disponível")
                return False
            
            # Verifica se PostgreSQL (pgvector) está rodando
            result = subprocess.run(
                "docker service ls | grep pgvector",
                shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                self.logger.warning("⚠️  PostgreSQL (pgvector) não encontrado - será necessário para o mapeamento de inboxes")
            else:
                self.logger.info("✅ PostgreSQL (pgvector) disponível")
            
            # Verifica se Chatwoot está rodando
            result = subprocess.run(
                "docker service ls | grep chatwoot",
                shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                self.logger.warning("⚠️  Chatwoot não encontrado - será necessário para integração")
            else:
                self.logger.info("✅ Chatwoot disponível")
            
            self.logger.info("✅ Pré-requisitos validados")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao validar pré-requisitos: {e}")
            return False
    
    def setup_dns_records(self) -> bool:
        """Configura registros DNS no Cloudflare"""
        try:
            self.logger.info("🌐 Configurando DNS para LivChatBridge...")
            
            # Obter domínio do usuário
            domain = self.get_user_input(
                "Digite o domínio para o LivChatBridge (ex: bridge.livchat.ai)",
                required=True
            )
            
            if not domain:
                self.logger.error("❌ Domínio é obrigatório")
                return False
            
            # Configurar DNS via Cloudflare
            cloudflare_api = get_cloudflare_api()
            if cloudflare_api and cloudflare_api.setup_dns_for_service("livchatbridge", [domain]):
                self.logger.info(f"✅ DNS configurado para {domain}")
                self.config['domain'] = domain
                return True
            else:
                self.logger.warning(f"⚠️  Configuração DNS manual necessária para {domain}")
                self.config['domain'] = domain
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro na configuração DNS: {e}")
            return False
    
    def collect_configuration(self) -> bool:
        """Coleta configurações necessárias do usuário"""
        try:
            self.logger.info("📋 Coletando configurações do LivChatBridge...")
            
            # URLs dos serviços
            chatwoot_url = self.get_user_input(
                "URL do Chatwoot (ex: https://chat.dev.livchat.ai)",
                required=True
            )
            if not chatwoot_url:
                self.logger.error("❌ URL do Chatwoot é obrigatória")
                return False
            
            gowa_url = self.get_user_input(
                "URL do GOWA (ex: https://gowa.dev.livchat.ai)",
                required=True
            )
            if not gowa_url:
                self.logger.error("❌ URL do GOWA é obrigatória")
                return False
            
            # Token do Chatwoot
            chatwoot_token = self.get_user_input(
                "Token de API do Chatwoot",
                required=True
            )
            if not chatwoot_token:
                self.logger.error("❌ Token do Chatwoot é obrigatório")
                return False
            
            # Credenciais do GOWA
            gowa_auth = self.get_user_input(
                "Credenciais GOWA (formato: user:password)",
                required=True
            )
            if not gowa_auth:
                self.logger.error("❌ Credenciais do GOWA são obrigatórias")
                return False
            
            # PostgreSQL (usar configurações padrão se disponível)
            postgres_password = self.get_user_input(
                "Senha do PostgreSQL (deixe vazio para usar padrão)",
                required=False
            )
            
            # Gerar webhook secret
            webhook_secret = secrets.token_urlsafe(32)
            
            # Salvar configurações
            self.config.update({
                'chatwoot_base_url': chatwoot_url,
                'gowa_base_url': gowa_url,
                'bridge_base_url': f"https://{self.config.get('domain', 'bridge.livchat.ai')}",
                'chatwoot_token': chatwoot_token,
                'gowa_auth': gowa_auth,
                'webhook_secret': webhook_secret,
                'postgres_host': 'pgvector',
                'postgres_username': 'postgres',
                'postgres_password': postgres_password or 'jLTDlNgqkWnHqnQM',
                'postgres_database': 'chatwoot',
                'postgres_port': '5432',
                'docker_image': 'livchatbridge:latest'
            })
            
            self.logger.info("✅ Configurações coletadas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao coletar configurações: {e}")
            return False
    
    def deploy_service(self) -> bool:
        """Deploy do LivChatBridge via Docker Swarm"""
        try:
            self.logger.info("🚀 Fazendo deploy do LivChatBridge...")
            if not self.network_name:
                self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
                return False
            
            # Preparar variáveis do template
            template_vars = {
                'service_name': self.service_name,
                'network_name': self.network_name,
                **self.config
            }
            
            # Deploy via Portainer (seguindo padrão dos outros módulos)
            success = self.portainer_api.deploy_service_complete(
                service_name=self.service_name,
                template_path="docker-compose/livchatbridge.yaml.j2",
                template_vars=template_vars,
                volumes=[],  # LivChatBridge não precisa de volumes persistentes
                wait_services=[self.service_name]
            )
            
            if not success:
                self.logger.error("❌ Falha no deploy do LivChatBridge")
                return False
            
            self.logger.info(f"✅ LivChatBridge deployado com sucesso")
            self.logger.info(f"🌐 Acesse: {self.config['bridge_base_url']}")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro no deploy: {e}")
            return False
    
    def post_installation_instructions(self) -> bool:
        """Instruções pós-instalação"""
        try:
            self.logger.info("📋 Instruções pós-instalação:")
            print(f"""
{self.colors.VERDE}✅ LivChatBridge instalado com sucesso!{self.colors.RESET}

{self.colors.AMARELO}🔧 Próximos passos:{self.colors.RESET}

1. {self.colors.BRANCO}Configurar webhook no Chatwoot:{self.colors.RESET}
   - Acesse: {self.config['chatwoot_base_url']}/app/accounts/1/settings/integrations/webhooks
   - URL: {self.config['bridge_base_url']}/webhook/chatwoot
   - Eventos: Todos os eventos disponíveis

2. {self.colors.BRANCO}Configurar webhook no GOWA:{self.colors.RESET}
   - Adicione as variáveis de ambiente no container GOWA:
     WHATSAPP_WEBHOOK={self.config['bridge_base_url']}/webhook/gowa
     WHATSAPP_WEBHOOK_SECRET={self.config['webhook_secret']}

3. {self.colors.BRANCO}Testar integração:{self.colors.RESET}
   - Health check: {self.config['bridge_base_url']}/
   - Logs: docker service logs -f {self.service_name}_{self.service_name}

{self.colors.VERDE}🎯 O LivChatBridge criará automaticamente inboxes no Chatwoot para novas instâncias GOWA!{self.colors.RESET}
            """)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro nas instruções: {e}")
            return False
    
    def run(self) -> bool:
        """Executa o setup completo do LivChatBridge (método abstrato da BaseSetup)"""
        return self.run_setup()
    
    def run_setup(self) -> bool:
        """Executa o setup completo do LivChatBridge"""
        try:
            self.logger.info("🚀 Iniciando setup do LivChatBridge...")
            
            if not self.network_name:
                self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
                return False
            
            # Validar pré-requisitos
            if not self.validate_prerequisites():
                return False
            
            # Configurar DNS
            if not self.setup_dns_records():
                return False
            
            # Coletar configurações
            if not self.collect_configuration():
                return False
            
            # Deploy do serviço
            if not self.deploy_service():
                return False
            
            # Instruções pós-instalação
            if not self.post_installation_instructions():
                return False
            
            self.logger.info("✅ Setup do LivChatBridge concluído com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro no setup: {e}")
            return False
