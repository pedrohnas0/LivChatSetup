#!/usr/bin/env python3
"""
Módulo de instalação do Traefik
Baseado no SetupOrionOriginal.sh - linhas 3654-3773
"""

import subprocess
import os
import time
from .base_setup import BaseSetup
from utils.template_engine import TemplateEngine
from utils.config_manager import ConfigManager

class TraefikSetup(BaseSetup):
    """Instalação e configuração do Traefik"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, email: str = None, network_name: str = None, config_manager: ConfigManager = None):
        super().__init__("Instalação do Traefik")
        self.email = email
        self.network_name = network_name
        self.config = config_manager or ConfigManager()
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Solicita email interativamente se não fornecido
        if not self.email:
            self.email = self._get_email_input()
            if not self.email:
                self.logger.error("Email para SSL é obrigatório")
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
        
        # Centralização perfeita
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_title = f"{self.BEGE}{clean_title}{self.RESET}"
        colored_line = centered_clean.replace(clean_title, colored_title)
            
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
    
    def _get_email_input(self) -> str:
        """Solicita email do usuário interativamente com sugestão do ConfigManager"""
        self._print_section_box("🔐 CONFIGURAÇÃO TRAEFIK - SSL")
        
        # Busca email padrão do ConfigManager
        default_email = self.config.get_user_email()
        
        while True:
            email = self.get_user_input("Email para certificados SSL", suggestion=default_email)
            
            # Valida email
            if email and '@' in email and '.' in email:
                return email
            else:
                print(f"{self.VERMELHO}❌ Email inválido! Digite um email válido.{self.RESET}")
    
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
        """Cria a rede overlay para o Traefik"""
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
    
    def create_traefik_stack(self) -> bool:
        """Cria o arquivo docker-compose do Traefik usando template"""
        try:
            # Inicializa template engine
            template_engine = TemplateEngine()
            
            # Variáveis para o template
            template_vars = {
                'network_name': self.network_name,
                'email': self.email,
                'log_level': 'INFO',
                'dashboard_domain': None,  # Pode ser configurado futuramente
                'dashboard_auth': None     # Pode ser configurado futuramente
            }
            
            # Renderiza template para arquivo
            stack_file = "/tmp/traefik-stack.yml"
            if not template_engine.render_to_file(
                'docker-compose/traefik.yaml.j2', 
                template_vars, 
                stack_file
            ):
                self.logger.error("Falha ao renderizar template do Traefik")
                return False
            
            self.logger.info(f"Stack do Traefik criada: {stack_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar stack do Traefik: {e}")
            return False

    
    def create_volume(self) -> bool:
        """Cria o volume para certificados SSL"""
        # Verifica se o volume já existe
        try:
            result = subprocess.run(
                "docker volume ls --filter name=vol_certificates --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "vol_certificates" in result.stdout:
                self.logger.info("Volume vol_certificates já existe")
                return True
        except Exception as e:
            self.logger.debug(f"Erro ao verificar volume: {e}")
        
        # Cria o volume
        return self.run_command(
            "docker volume create vol_certificates",
            "criação do volume vol_certificates"
        )
    
    def deploy_traefik_stack(self) -> bool:
        """Faz o deploy da stack do Traefik"""
        return self.run_command(
            "docker stack deploy --prune --resolve-image always -c /tmp/traefik-stack.yml traefik",
            "deploy da stack do Traefik",
            timeout=120
        )
    
    def wait_for_traefik(self, timeout: int = 180) -> bool:
        """Aguarda o Traefik ficar online"""
        self.logger.info(f"Aguardando Traefik ficar online (timeout: {timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Verifica se o serviço está rodando
                result = subprocess.run(
                    "docker service ls --filter name=traefik_traefik --format '{{.Replicas}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and "1/1" in result.stdout:
                    self.logger.info("Traefik está online")
                    return True
                    
                self.logger.debug("Traefik ainda não está pronto, aguardando...")
                time.sleep(10)
                
            except Exception as e:
                self.logger.debug(f"Erro ao verificar status do Traefik: {e}")
                time.sleep(10)
        
        self.logger.error("Timeout aguardando Traefik ficar online")
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
            
            if result.returncode == 0 and "traefik" in result.stdout:
                self.logger.info("Stack do Traefik encontrada")
                
                # Verifica se as portas estão abertas
                port_checks = [
                    ("80", "HTTP"),
                    ("443", "HTTPS")
                ]
                
                for port, protocol in port_checks:
                    if self.check_port_listening(port):
                        self.logger.info(f"Porta {port} ({protocol}) está aberta")
                    else:
                        self.logger.warning(f"Porta {port} ({protocol}) não está respondendo")
                
                return True
            else:
                self.logger.error("Stack do Traefik não encontrada")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar instalação: {e}")
            return False
    
    def check_port_listening(self, port: str) -> bool:
        """Verifica se uma porta está sendo escutada"""
        try:
            result = subprocess.run(
                f"netstat -tlnp | grep :{port}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and port in result.stdout
        except Exception as e:
            self.logger.debug(f"Erro ao verificar porta {port}: {e}")
            return False
    
    def run(self) -> bool:
        """Executa a instalação completa do Traefik"""
        self.log_step_start("Instalação do Traefik")
        
        if not self.validate_prerequisites():
            return False
        
        # Cria a rede overlay
        if not self.create_network():
            return False
        
        # Cria o volume para certificados
        if not self.create_volume():
            return False
        
        # Cria o arquivo da stack
        if not self.create_traefik_stack():
            return False
        
        # Faz o deploy da stack
        if not self.deploy_traefik_stack():
            return False
        
        # Aguarda o Traefik ficar online
        if not self.wait_for_traefik():
            self.logger.warning("Traefik pode não estar totalmente online, mas foi instalado")
        
        # Verifica instalação
        if not self.verify_installation():
            return False
        
        duration = self.get_duration()
        self.logger.info(f"Instalação do Traefik concluída ({duration:.2f}s)")
        self.logger.info(f"Traefik configurado com email: {self.email}")
        
        # Sessão de sucesso seguindo padrão visual
        self._show_success_summary(self.email)
        
        self.log_step_complete("Instalação do Traefik")
        
        return True
    
    def _show_success_summary(self, email: str):
        """Exibe sessão de sucesso do Traefik seguindo padrão visual"""
        self._print_section_box("✅ TRAEFIK INSTALADO COM SUCESSO!")
        
        print(f"{self.VERDE}🔐 Proxy Reverso: {self.BRANCO}Configurado{self.RESET}")
        print(f"{self.VERDE}📜 Certificados SSL: {self.BRANCO}Let's Encrypt{self.RESET}")
        print(f"{self.VERDE}📧 Email SSL: {self.BRANCO}{email}{self.RESET}")
        print()
        print(f"{self.BEGE}📝 CARACTERÍSTICAS:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} Certificados SSL automáticos para todos os serviços")
        print(f"   {self.VERDE}•{self.RESET} Renovação automática dos certificados")
        print(f"   {self.VERDE}•{self.RESET} Balanceamento de carga integrado")
        print(f"   {self.VERDE}•{self.RESET} Dashboard de monitoramento disponível")
        print()
        print(f"{self.LARANJA}🚀 Traefik pronto para receber suas aplicações!{self.RESET}")

def main():
    """Função principal para teste do módulo"""
    import sys
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Uso: python3 traefik_setup.py <email> [rede]")
        print("Exemplo: python3 traefik_setup.py admin@meudominio.com")
        sys.exit(1)
    
    email = sys.argv[1]
    network_name = sys.argv[2] if len(sys.argv) > 2 else None
    if not network_name:
        print("Erro: É obrigatório informar o nome da rede Docker como 2º argumento.")
        sys.exit(1)
    
    setup = TraefikSetup(email, network_name)
    
    if setup.run():
        print(f"Traefik instalado com sucesso com email: {email}")
    else:
        print("Falha na instalação do Traefik")
        sys.exit(1)

if __name__ == "__main__":
    main()
