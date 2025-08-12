#!/usr/bin/env python3
"""
Módulo de setup do GOWA (Go WhatsApp Web Multi Device)
Baseado na documentação oficial: https://github.com/aldinokemal/go-whatsapp-web-multidevice
Inclui integração com Cloudflare para DNS automático
"""

import os
import secrets
from setup.base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.template_engine import TemplateEngine
from utils.cloudflare_api import get_cloudflare_api

class GowaSetup(BaseSetup):
    """Setup do GOWA com integração Cloudflare"""
    
    def __init__(self, network_name: str = None):
        super().__init__("gowa")
        self.service_name = "gowa"
        self.portainer_api = PortainerAPI()
        self.template_engine = TemplateEngine()
        self.network_name = network_name
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para o GOWA"""
        self.logger.info("🔍 Validando pré-requisitos do GOWA...")
        
        # GOWA é uma aplicação standalone, não requer dependências específicas
        # Apenas verifica se o Docker está funcionando
        try:
            import subprocess
            if not self.network_name:
                self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
                return False
            result = subprocess.run(
                "docker --version",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error("❌ Docker não está disponível")
                return False
            
            self.logger.info("✅ Docker disponível")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao validar pré-requisitos: {e}")
            return False
    
    def setup_dns_records(self) -> bool:
        """Configura registros DNS via Cloudflare"""
        self.logger.info("🌐 Configurando DNS no Cloudflare...")
        
        try:
            # Coleta informações do usuário
            while True:
                domain = input("Digite o domínio para o GOWA (ex: gowa.seudominio.com): ").strip()
                if domain:
                    break
                print("❌ Domínio é obrigatório!")
            
            # Configura DNS via Cloudflare
            cloudflare_api = get_cloudflare_api()
            if not cloudflare_api:
                self.logger.error("❌ API Cloudflare não configurada")
                return False
            
            # Cria registro CNAME
            # Target padrão para o ambiente (pode ser configurado conforme necessário)
            target = "ptn.dev.livchat.ai"  # Target padrão do ambiente
            success = cloudflare_api.create_cname_record(domain, target)
            if not success:
                self.logger.error(f"❌ Falha ao criar registro DNS para {domain}")
                return False
            
            self.logger.info(f"✅ DNS configurado: {domain}")
            
            # Armazena configurações na instância para uso posterior
            self.domain = domain
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar DNS: {e}")
            return False
    
    def deploy_service(self) -> bool:
        """Deploy do GOWA via Portainer"""
        self.logger.info("🚀 Iniciando deploy do GOWA...")
        
        try:
            # Verifica se o domínio foi configurado
            if not hasattr(self, 'domain') or not self.domain:
                self.logger.error("❌ Domínio não configurado. Execute setup_dns_records primeiro.")
                return False
            
            # Exigir network_name
            if not self.network_name:
                self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
                return False

            # Gera autenticação automática
            import base64
            password_bytes = secrets.token_bytes(48)  # 48 bytes = 64 caracteres base64
            basic_auth_password = base64.b64encode(password_bytes).decode('utf-8')
            basic_auth = f"admin:{basic_auth_password}"
            
            # Prepara variáveis do template
            template_vars = {
                'service_name': self.service_name,
                'domain': self.domain,
                'network_name': self.network_name,
                'basic_auth': basic_auth
            }
            
            # Deploy via Portainer
            success = self.portainer_api.deploy_service_complete(
                service_name=self.service_name,
                template_path="docker-compose/gowa.yaml.j2",
                template_vars=template_vars,
                volumes=[f"{self.service_name}_data"],
                wait_services=[self.service_name]
            )
            
            if not success:
                self.logger.error("❌ Falha no deploy do GOWA")
                return False
            
            # Armazena configurações na instância
            self.basic_auth_password = basic_auth_password
            self.deployed = True
            
            # Salva credenciais em arquivo
            self._save_credentials(basic_auth_password)
            
            self.logger.info("✅ GOWA deployado com sucesso!")
            self.logger.info(f"🌐 Acesse: https://{self.domain}")
            self.logger.info("🔐 Credenciais salvas em /root/dados_vps/dados_gowa")
            self.logger.info("📱 Configure seu WhatsApp através da interface web")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro no deploy: {e}")
            return False
    
    def _save_credentials(self, password: str) -> None:
        """Salva credenciais do GOWA em arquivo"""
        try:
            credentials_text = f"""GOWA (WhatsApp API Multi Device) - Credenciais de Acesso

URL: https://{self.domain}
Usuário: admin
Senha: {password}

Configuração:
1. Acesse a URL acima
2. Faça login com as credenciais
3. Escaneie o QR Code com seu WhatsApp
4. Use a API REST para enviar mensagens

Data de instalação: {self.start_time.strftime('%d/%m/%Y %H:%M:%S')}
"""
            
            import os
            os.makedirs("/root/dados_vps", exist_ok=True)
            with open("/root/dados_vps/dados_gowa", 'w', encoding='utf-8') as f:
                f.write(credentials_text)
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
    
    def show_access_info(self) -> bool:
        """Exibe informações de acesso ao GOWA"""
        try:
            if not hasattr(self, 'domain') or not self.domain:
                self.logger.error("❌ Configurações não encontradas")
                return False
            
            self.logger.info("📋 Informações de Acesso ao GOWA:")
            self.logger.info(f"🌐 URL: https://{self.domain}")
            self.logger.info("🔐 Credenciais de Acesso:")
            self.logger.info(f"   Usuário: admin")
            self.logger.info(f"   Senha: {getattr(self, 'basic_auth_password', 'N/A')}")
            self.logger.info("📱 Para configurar WhatsApp:")
            self.logger.info("   1. Acesse a URL acima")
            self.logger.info("   2. Faça login com as credenciais acima")
            self.logger.info("   3. Escaneie o QR Code com seu WhatsApp")
            self.logger.info("   4. Use a API REST para enviar mensagens")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao exibir informações: {e}")
            return False
    
    def run(self) -> bool:
        """Execução principal do setup do GOWA"""
        self.logger.info("🚀 Iniciando setup do GOWA (Go WhatsApp Web Multi Device)")
        
        try:
            # 1. Validar pré-requisitos
            if not self.validate_prerequisites():
                return False
            
            # 2. Configurar DNS
            if not self.setup_dns_records():
                return False
            
            # 3. Deploy do serviço
            if not self.deploy_service():
                return False
            
            # 4. Exibir informações de acesso
            self.show_access_info()
            
            self.logger.info("✅ Setup do GOWA concluído com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro no setup do GOWA: {e}")
            return False
