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
from utils.portainer_api import PortainerAPI

class PortainerSetup(BaseSetup):
    """Instalação e configuração do Portainer"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, domain: str = None, network_name: str = None, config_manager: ConfigManager = None, auto_mode: bool = False):
        super().__init__("Instalação do Portainer")
        self.domain = domain
        self.network_name = network_name
        self.config = config_manager or ConfigManager()
        self.auto_mode = auto_mode  # Modo automático quando é dependência
        
    def is_portainer_running(self) -> bool:
        """Verifica se Portainer já está rodando"""
        try:
            result = subprocess.run(
                "docker service ls --filter name=portainer_agent --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "portainer_agent" in result.stdout
        except Exception as e:
            self.logger.debug(f"Erro ao verificar Portainer: {e}")
            return False

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
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal de forma segura"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback
    
    def _print_section_box(self, title: str, width: int = None):
        """Cria box de seção menor seguindo padrão do projeto"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(60, terminal_width - 10)
        
        # Remove códigos de cor para calcular tamanho real
        import re
        clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
        
        line = "─" * (width - 1)
        print(f"\n{self.CINZA}╭{line}╮{self.RESET}")
        
        # Centralização perfeita usando Python nativo
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
            
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None) -> str:
        """Coleta entrada do usuário com sugestão opcional seguindo padrão do projeto"""
        try:
            if suggestion:
                full_prompt = f"{prompt} (Enter para '{suggestion}' ou digite outro valor)"
            else:
                full_prompt = prompt
                
            value = input(f"{full_prompt}: ").strip()
            
            # Se não digitou nada e há sugestão, usa a sugestão
            if not value and suggestion:
                return suggestion
                
            if required and not value:
                self.logger.warning("Valor obrigatório não fornecido")
                return None
                
            return value if value else None
            
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return None
    
    def _get_domain_input(self) -> str:
        """Solicita domínio do usuário interativamente com sugestão inteligente"""
        self._print_section_box("🐳 CONFIGURAÇÃO PORTAINER")
        
        # Gera sugestão baseada na configuração DNS
        suggested_domain = self.config.suggest_domain("ptn")
        
        while True:
            domain = self.get_user_input("Domínio do Portainer", suggestion=suggested_domain)
            
            # Valida domínio
            if domain and '.' in domain:
                return domain
            else:
                print(f"{self.VERMELHO}❌ Domínio inválido! Digite um domínio válido.{self.RESET}")
    
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
        
        # Verifica se deve pular (quando é dependência e já está rodando)
        if self.auto_mode and self.is_portainer_running():
            self.logger.info("Portainer já está rodando, pulando configuração")
            self.log_step_complete("Instalação do Portainer")
            return True  # Sucesso - não precisa instalar
            
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
        
        if self.auto_mode:
            # Modo automático (dependência) - testa silenciosamente se credenciais já funcionam
            portainer_api = PortainerAPI()
            if portainer_api.test_credentials(self.domain, suggested_credentials['username'], suggested_credentials['password'], silent=True):
                # Credenciais já funcionam - salva automaticamente
                self._show_auto_mode_summary(suggested_credentials)
                self.config.save_app_credentials("portainer", {
                    "url": f"https://{self.domain}",
                    "username": suggested_credentials['username'],
                    "password": suggested_credentials['password']
                })
                self.logger.info("✅ Credenciais testadas e salvas automaticamente")
            else:
                # Credenciais não funcionam - vai para fluxo normal de sucesso (primeira instalação)
                self.logger.warning("⚠️ Conta de administrador ainda não foi criada no Portainer")
                self._show_success_summary_with_suggested_credentials(suggested_credentials)
                
                # Confirma se o usuário criou a conta com as credenciais sugeridas
                if not self._confirm_account_creation_with_suggested_credentials(suggested_credentials):
                    self.logger.error("❌ Criação da conta não confirmada. Configure manualmente antes de continuar.")
                    return False
                
                # Coleta credenciais reais confirmadas pelo usuário
                real_credentials = self._collect_real_credentials(suggested_credentials)
                if real_credentials:
                    # Salva as credenciais reais
                    self.config.save_app_credentials("portainer", {
                        "url": f"https://{self.domain}",
                        "username": real_credentials['username'],
                        "password": real_credentials['password']
                    })
        else:
            # Modo manual (selecionado pelo usuário) - configuração interativa
            self._show_success_summary_with_suggested_credentials(suggested_credentials)
            
            # Confirma se o usuário criou a conta com as credenciais sugeridas
            if not self._confirm_account_creation_with_suggested_credentials(suggested_credentials):
                self.logger.error("❌ Criação da conta não confirmada. Configure manualmente antes de continuar.")
                return False
            
            # Coleta credenciais reais confirmadas pelo usuário
            real_credentials = self._collect_real_credentials(suggested_credentials)
            if real_credentials:
                # Salva as credenciais reais
                self.config.save_app_credentials("portainer", {
                    "url": f"https://{self.domain}",
                    "username": real_credentials['username'],
                    "password": real_credentials['password']
                })
            
            # Pergunta sobre mais instalações
            self._ask_for_more_installations()
        
        self.logger.info(f"✅ Acesso ao Portainer confirmado!")
        self.logger.info(f"Configuração salva no ConfigManager: {self.domain}")
        self.log_step_complete("Instalação do Portainer")
        
        return True
    
    def _suggest_portainer_credentials(self) -> dict:
        """Sugere credenciais para o Portainer (email padrão + senha gerada)"""
        # Obtém email padrão ou pergunta
        default_email = self.config.get_user_email()
        if not default_email:
            self._print_section_box("📧 EMAIL PADRÃO NECESSÁRIO")
            default_email = self.get_user_input("Email para usar como padrão", required=True)
            if default_email:
                self.config.set_user_email(default_email)
        
        # Gera senha segura de 64 caracteres
        suggested_password = self.config.generate_secure_password(64)
        
        return {
            "username": default_email,
            "password": suggested_password
        }
    
    def _collect_real_credentials(self, suggested_credentials: dict) -> dict:
        """Coleta as credenciais reais usadas pelo usuário (com sugestão)"""
        self._print_section_box("📝 CONFIRMAÇÃO DAS CREDENCIAIS REAIS")
        
        print(f"{self.BEGE}Confirme os dados reais que você usou para criar a conta:{self.RESET}")
        print()
        
        # Solicita email com sugestão
        real_email = self.get_user_input("Email usado na conta", suggestion=suggested_credentials['username'])
        
        # Solicita senha com sugestão
        real_password = self.get_user_input("Senha usada na conta", suggestion=suggested_credentials['password'])
        
        if real_email and real_password:
            print(f"{self.VERDE}✅ Credenciais reais confirmadas e salvas!{self.RESET}")
            return {
                "username": real_email,
                "password": real_password
            }
        
        return None
    
    def _ask_for_more_installations(self):
        """Pergunta se usuário quer fazer mais instalações (padrão do menu principal)"""
        print()
        self._print_section_box("🚀 PRÓXIMOS PASSOS")
        
        print(f"{self.BEGE}O Portainer foi instalado com sucesso!{self.RESET}")
        print(f"{self.VERDE}✅{self.RESET} URL: https://{self.domain}")
        print(f"{self.VERDE}✅{self.RESET} Conta administrativa criada")
        print(f"{self.VERDE}✅{self.RESET} Pronto para gerenciar containers")
        print()
        
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para instalar mais aplicações ou {self.VERMELHO}Ctrl+C{self.RESET} {self.BEGE}para encerrar...{self.RESET}")
    
    def _show_auto_mode_summary(self, credentials: dict):
        """Exibe resumo simplificado para modo automático (dependência)"""
        self._print_section_box("✅ PORTAINER INSTALADO (DEPENDÊNCIA)")
        
        print(f"{self.VERDE}🌐 URL: {self.BRANCO}https://{self.domain}{self.RESET}")
        print(f"{self.VERDE}🔧 Status: {self.BRANCO}Pronto para gerenciar containers{self.RESET}")
        print()
        print(f"{self.BEGE}📝 Credenciais salvas automaticamente para automação:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Usuario: {credentials['username']}")
        print(f"   {self.VERDE}•{self.RESET} Senha: [gerada automaticamente]")
        print()
        print(f"{self.LARANJA}ℹ️  Portainer configurado como dependência - prosseguindo com instalação...{self.RESET}")
    
    def _show_success_summary_with_suggested_credentials(self, credentials: dict):
        """Exibe sessão de sucesso com credenciais que o usuário DEVE usar seguindo padrão visual"""
        self._print_section_box("✅ PORTAINER INSTALADO COM SUCESSO!")
        
        print(f"{self.VERDE}🌐 URL de Acesso: {self.BRANCO}https://{self.domain}{self.RESET}")
        print()
        print(f"{self.BEGE}👤 CREDENCIAIS SUGERIDAS PARA CRIAR A CONTA ADMINISTRADOR:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Email/Usuário: {self.BRANCO}{credentials['username']}{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Senha: {self.BRANCO}{credentials['password']}{self.RESET}")
        print()
        print(f"{self.BEGE}📝 INSTRUÇÕES:{self.RESET}")
        print(f"   {self.VERDE}1.{self.RESET} Acesse {self.BRANCO}https://{self.domain}{self.RESET}")
        print(f"   {self.VERDE}2.{self.RESET} Crie o primeiro usuário com os dados sugeridos acima")
        print(f"   {self.VERDE}3.{self.RESET} Use preferencialmente o email e senha mostrados")
        print(f"   {self.VERDE}4.{self.RESET} Confirme que conseguiu fazer login")
        print()
        print(f"{self.LARANJA}⚠️  DICA: Use as credenciais sugeridas para facilitar a automação!{self.RESET}")
    
    def _handle_manual_account_creation_required(self, credentials: dict) -> bool:
        """Gerencia criação manual da conta quando auto_mode falha na validação"""
        self._print_section_box("⚠️ AÇÃO NECESSÁRIA: CRIAR CONTA MANUALMENTE")
        
        print(f"{self.VERMELHO}❌ PROBLEMA DETECTADO:{self.RESET}")
        print(f"   O Portainer foi instalado mas ainda não tem uma conta de administrador criada.")
        print()
        
        print(f"{self.BEGE}📝 INSTRUÇÕES PARA RESOLVER:{self.RESET}")
        print(f"   {self.VERDE}1.{self.RESET} Acesse {self.BRANCO}https://{self.domain}{self.RESET}")
        print(f"   {self.VERDE}2.{self.RESET} Crie o primeiro usuário administrador usando as credenciais abaixo:")
        print()
        print(f"      {self.VERDE}•{self.RESET} Email/Usuário: {self.BRANCO}{credentials['username']}{self.RESET}")
        print(f"      {self.VERDE}•{self.RESET} Senha: {self.BRANCO}{credentials['password']}{self.RESET}")
        print()
        print(f"   {self.VERDE}3.{self.RESET} Confirme que conseguiu fazer login")
        print(f"   {self.VERDE}4.{self.RESET} Retorne aqui e pressione Enter para continuar")
        print()
        print(f"{self.LARANJA}⚠️  IMPORTANTE: Use exatamente as credenciais sugeridas para manter a automação!{self.RESET}")
        print()
        
        # Aguarda confirmação do usuário
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}após criar a conta no Portainer...{self.RESET}")
        
        # Testa as credenciais novamente
        portainer_api = PortainerAPI()
        print(f"\n{self.BEGE}🧪 Testando credenciais...{self.RESET}")
        
        if portainer_api.test_credentials(self.domain, credentials['username'], credentials['password']):
            print(f"{self.VERDE}✅ Credenciais confirmadas! Conta criada com sucesso.{self.RESET}")
            
            # Salva as credenciais após confirmação
            self.config.save_app_credentials("portainer", {
                "url": f"https://{self.domain}",
                "username": credentials['username'],
                "password": credentials['password']
            })
            
            print(f"{self.BEGE}ℹ️  Credenciais salvas para automação - prosseguindo com instalação...{self.RESET}")
            return True
        else:
            print(f"{self.VERMELHO}❌ Credenciais ainda não funcionam.{self.RESET}")
            print(f"{self.BEGE}Verifique se você criou a conta corretamente e tente novamente.{self.RESET}")
            return False
    
    def _confirm_account_creation_with_suggested_credentials(self, credentials: dict) -> bool:
        """Confirma se o usuário criou a conta (seguindo padrão visual)"""
        self._print_section_box("🔍 CONFIRMAÇÃO DE CRIAÇÃO DA CONTA")
        
        print(f"{self.BEGE}Confirme que você:{self.RESET}")
        print(f"   {self.VERDE}✓{self.RESET} Acessou https://{self.domain}")
        print(f"   {self.VERDE}✓{self.RESET} Criou uma conta de administrador")
        print(f"   {self.VERDE}✓{self.RESET} Conseguiu fazer login normalmente")
        print()
        
        # Usar padrão "Enter para continuar" como nos outros módulos
        input(f"{self.BEGE}Pressione {self.VERDE}Enter{self.RESET} {self.BEGE}para confirmar que a conta foi criada...{self.RESET}")
        
        print(f"{self.VERDE}✅ Criação da conta confirmada!{self.RESET}")
        return True
    

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
