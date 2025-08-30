#!/usr/bin/env python3
"""
Módulo de instalação do Portainer
Baseado no SetupOrionOriginal.sh - linhas 3774-3870
"""

import subprocess
import os
import time
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine
from utils.cloudflare_api import get_cloudflare_api
from utils.config_manager import ConfigManager

class PortainerSetup(BaseSetup):
    """Instalação e configuração do Portainer"""
    
    def __init__(self, domain: str = None, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do Portainer")
        self.domain = domain
        self.network_name = network_name
        self.config = config_manager or ConfigManager()
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Solicita domínio interativamente se não fornecido
        if not self.domain:
            self.domain = self._get_domain_input()
            if not self.domain:
                self.logger.error("Domínio do Portainer é obrigatório")
                return False
            
        # Verifica se Docker está instalado
        if not self.is_docker_running():
            self.logger.error("Docker não está rodando")
            return False
            
        # Verifica se Docker Swarm está ativo
        if not self.is_swarm_active():
            self.logger.error("Docker Swarm não está ativo")
            return False
        # Exige nome da rede
        if not self.network_name:
            self.logger.error("Nome da rede Docker é obrigatório. Forneça via parâmetro 'network_name'.")
            return False
            
        return True

    def setup_dns_record(self) -> bool:
        """Cria ou garante registro DNS A para o domínio do Portainer no Cloudflare."""
        try:
            self.logger.info("🌐 Configurando DNS do Portainer no Cloudflare (registro A)...")
            cf = get_cloudflare_api(self.logger, self.config)
            if not cf:
                self.logger.error("❌ API Cloudflare não configurada")
                return False
            
            comment = "Portainer"
            # ip=None faz com que ensure_a_record detecte o IP público automaticamente
            # proxied=False => DNS Only (sem proxy da Cloudflare)
            if cf.ensure_a_record(self.domain, ip=None, proxied=False, comment=comment):
                self.logger.info(f"✅ Registro A garantido para {self.domain} (comentário: {comment})")
                return True
            
            self.logger.error(f"❌ Falha ao garantir registro A para {self.domain}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar DNS do Portainer: {e}")
            return False
    
    def _get_domain_input(self) -> str:
        """Solicita domínio do usuário interativamente com sugestão inteligente"""
        print(f"\n🐳 CONFIGURAÇÃO PORTAINER")
        print("─" * 30)
        
        # Gera sugestão baseada na configuração DNS
        suggested_domain = self.config.suggest_domain("ptn")
        
        while True:
            if suggested_domain:
                prompt = f"Domínio do Portainer (Enter para '{suggested_domain}' ou digite outro)"
            else:
                prompt = "Digite o domínio para o Portainer (ex: ptn.seudominio.com)"
                
            domain = input(f"{prompt}: ").strip()
            
            # Se não digitou nada e tem sugestão, usa a sugestão
            if not domain and suggested_domain:
                return suggested_domain
            
            # Valida domínio
            if domain and '.' in domain:
                return domain
            else:
                print("❌ Domínio inválido! Digite um domínio válido.")
    
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
            return result.returncode == 0 and "active" in result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Erro ao verificar Swarm: {e}")
            return False
    
    def create_network(self) -> bool:
        """Cria a rede overlay para o Portainer"""
        # Verifica se a rede já existe
        try:
            result = subprocess.run(
                f"docker network ls --filter name={self.network_name} --format '{{{{.Name}}}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and self.network_name in result.stdout:
                self.logger.info(f"Rede {self.network_name} já existe")
                return True
        except Exception as e:
            self.logger.debug(f"Erro ao verificar rede: {e}")
        
        # Cria a rede
        return self.run_command(
            f"docker network create --driver=overlay {self.network_name}",
            f"criação da rede {self.network_name}"
        )
    
    def create_volume(self) -> bool:
        """Cria o volume para dados do Portainer"""
        # Verifica se o volume já existe
        try:
            result = subprocess.run(
                "docker volume ls --filter name=portainer_data --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "portainer_data" in result.stdout:
                self.logger.info("Volume portainer_data já existe")
                return True
        except Exception as e:
            self.logger.debug(f"Erro ao verificar volume: {e}")
        
        # Cria o volume
        return self.run_command(
            "docker volume create portainer_data",
            "criação do volume portainer_data"
        )
    
    def create_portainer_stack(self) -> bool:
        """Cria o arquivo docker-compose do Portainer usando template"""
        try:
            # Inicializa template engine
            template_engine = TemplateEngine()
            
            # Variáveis para o template
            template_vars = {
                'network_name': self.network_name,
                'portainer_domain': self.domain,
                'auth_middleware': None  # Pode ser configurado futuramente
            }
            
            # Renderiza template para arquivo
            stack_file = "/tmp/portainer-stack.yml"
            if not template_engine.render_to_file(
                'docker-compose/portainer.yaml.j2', 
                template_vars, 
                stack_file
            ):
                self.logger.error("Falha ao renderizar template do Portainer")
                return False
            
            self.logger.info(f"Stack do Portainer criada: {stack_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar stack do Portainer: {e}")
            return False
    
    def deploy_portainer_stack(self) -> bool:
        """Faz o deploy da stack do Portainer"""
        return self.run_command(
            "docker stack deploy --prune --resolve-image always -c /tmp/portainer-stack.yml portainer",
            "deploy da stack do Portainer",
            timeout=120
        )
    
    def wait_for_portainer(self, timeout: int = 300) -> bool:
        """Aguarda o Portainer ficar online"""
        self.logger.info(f"Aguardando Portainer ficar online (timeout: {timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Verifica se o serviço está rodando
                result = subprocess.run(
                    "docker service ls --filter name=portainer_portainer --format '{{.Replicas}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and "1/1" in result.stdout:
                    self.logger.info("Portainer está online")
                    return True
                    
                self.logger.debug("Portainer ainda não está pronto, aguardando...")
                time.sleep(10)
                
            except Exception as e:
                self.logger.debug(f"Erro ao verificar status do Portainer: {e}")
                time.sleep(10)
        
        self.logger.error("Timeout aguardando Portainer ficar online")
        return False
    
    def verify_installation(self) -> bool:
        """Verifica se a instalação foi bem-sucedida"""
        # Verifica se a stack foi criada
        try:
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "portainer" in result.stdout:
                self.logger.info("Stack do Portainer encontrada")
                return True
            else:
                self.logger.error("Stack do Portainer não encontrada")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar instalação: {e}")
            return False
    
    def run(self) -> bool:
        """Executa a instalação completa do Portainer"""
        self.log_step_start("Instalação do Portainer")
        
        if not self.validate_prerequisites():
            return False
        
        # Configura/garante DNS A no Cloudflare apontando para o IP público
        if not self.setup_dns_record():
            return False
        
        # Cria a rede overlay
        if not self.create_network():
            return False
        
        # Cria o volume
        if not self.create_volume():
            return False
        
        # Cria o arquivo da stack
        if not self.create_portainer_stack():
            return False
        
        # Faz o deploy da stack
        if not self.deploy_portainer_stack():
            return False
        
        # Aguarda o Portainer ficar online
        if not self.wait_for_portainer():
            self.logger.warning("Portainer pode não estar totalmente online, mas foi instalado")
        
        # Verifica instalação
        if not self.verify_installation():
            return False
        
        # Salva configurações do Portainer no ConfigManager
        self.config.save_app_config("portainer", {
            "domain": self.domain,
            "url": f"https://{self.domain}",
            "network_name": self.network_name,
            "installed": True,
            "installation_method": "auto"
        })
        
        duration = self.get_duration()
        self.logger.info(f"Instalação do Portainer concluída ({duration:.2f}s)")
        
        # Sugere credenciais que o usuário deve usar
        suggested_credentials = self._suggest_portainer_credentials()
        if not suggested_credentials:
            self.logger.error("❌ Erro ao gerar credenciais sugeridas.")
            return False
        
        # Sessão de destaque de sucesso com as credenciais sugeridas
        self._show_success_summary_with_suggested_credentials(suggested_credentials)
        
        # Confirma se o usuário criou a conta com as credenciais sugeridas
        if not self._confirm_account_creation_with_suggested_credentials(suggested_credentials):
            self.logger.error("❌ Criação da conta não confirmada. Configure manualmente antes de continuar.")
            return False
        
        self.logger.info(f"✅ Acesso ao Portainer confirmado!")
        self.logger.info(f"Configuração salva no ConfigManager: {self.domain}")
        self.log_step_complete("Instalação do Portainer")
        
        return True
    
    def _suggest_portainer_credentials(self) -> dict:
        """Sugere credenciais para o Portainer (email padrão + senha gerada)"""
        # Obtém email padrão ou pergunta
        default_email = self.config.get_user_email()
        if not default_email:
            print(f"\n📧 EMAIL PADRÃO NECESSÁRIO")
            print("─" * 30)
            default_email = input("Digite seu email para usar como padrão: ").strip()
            if default_email:
                self.config.set_user_email(default_email)
        
        # Gera senha segura de 64 caracteres
        suggested_password = self.config.generate_secure_password(64)
        
        return {
            "username": default_email,
            "password": suggested_password
        }
    
    def _show_success_summary_with_suggested_credentials(self, credentials: dict):
        """Exibe sessão de sucesso com credenciais que o usuário DEVE usar"""
        print(f"\n" + "=" * 70)
        print(f"🎉 PORTAINER INSTALADO COM SUCESSO!")
        print(f"=" * 70)
        print(f"")
        print(f"🌐 URL de Acesso: https://{self.domain}")
        print(f"")
        print(f"👤 CREDENCIAIS PARA CRIAR A CONTA ADMINISTRADOR:")
        print(f"   • Email/Usuário: {credentials['username']}")
        print(f"   • Senha: {credentials['password']}")
        print(f"")
        print(f"📝 INSTRUÇÕES:")
        print(f"   1. Acesse https://{self.domain}")
        print(f"   2. Crie o primeiro usuário com os dados EXATOS acima")
        print(f"   3. Use EXATAMENTE o email e senha mostrados")
        print(f"   4. Confirme que conseguiu fazer login")
        print(f"")
        print(f"⚠️  IMPORTANTE: Use exatamente esses dados para a automação funcionar!")
        print(f"=" * 70)
        print(f"")
    
    def _confirm_account_creation_with_suggested_credentials(self, credentials: dict) -> bool:
        """Confirma se o usuário criou a conta com as credenciais sugeridas"""
        while True:
            print(f"🔍 CONFIRMAÇÃO DE CRIAÇÃO DA CONTA")
            print(f"─" * 40)
            print(f"")
            print(f"Confirme que você:")
            print(f"✓ Acessou https://{self.domain}")
            print(f"✓ Criou conta com email: {credentials['username']}")
            print(f"✓ Usou a senha exata mostrada acima")
            print(f"✓ Conseguiu fazer login normalmente")
            print(f"")
            
            resposta = input("Você criou a conta com os dados exatos mostrados? (s/n): ").strip().lower()
            
            if resposta in ['s', 'sim', 'y', 'yes']:
                # Salva as credenciais no ConfigManager
                self.config.save_app_credentials("portainer", {
                    "url": f"https://{self.domain}",
                    "username": credentials['username'],
                    "password": credentials['password']
                })
                print(f"✅ Credenciais confirmadas e salvas!")
                return True
            elif resposta in ['n', 'nao', 'não', 'no']:
                print(f"\n❌ Conta não criada com as credenciais corretas.")
                print(f"🔧 Você DEVE usar exatamente:")
                print(f"   • Email: {credentials['username']}")
                print(f"   • Senha: {credentials['password']}")
                print(f"")
                print(f"🔄 Tente novamente ou cancele a instalação.")
                retry = input("Tentar novamente? (s/n): ").strip().lower()
                if retry not in ['s', 'sim', 'y', 'yes']:
                    return False
                continue
            else:
                print("❌ Responda com 's' (sim) ou 'n' (não)")
                continue
    

def main():
    """Função principal para teste do módulo"""
    import sys
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Uso: python3 portainer_setup.py <dominio> [rede]")
        print("Exemplo: python3 portainer_setup.py portainer.meudominio.com")
        sys.exit(1)
    
    domain = sys.argv[1]
    network_name = sys.argv[2] if len(sys.argv) > 2 else None
    if not network_name:
        print("Erro: É obrigatório informar o nome da rede Docker como 2º argumento.")
        sys.exit(1)
    
    setup = PortainerSetup(domain, network_name)
    
    if setup.run():
        print(f"Portainer instalado com sucesso: https://{domain}")
    else:
        print("Falha na instalação do Portainer")
        sys.exit(1)

if __name__ == "__main__":
    main()
