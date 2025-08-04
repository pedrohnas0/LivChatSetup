#!/usr/bin/env python3
"""
Coordenador de Módulos
Simplifica a execução e gerenciamento dos módulos de setup
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import setup_logging
from setup.basic_setup import SystemSetup as BasicSetup
from setup.hostname_setup import HostnameSetup
from setup.docker_setup import DockerSetup
from setup.traefik_setup import TraefikSetup
from setup.portainer_setup import PortainerSetup
from setup.cleanup_setup import CleanupSetup

class ModuleCoordinator:
    """Coordenador simplificado dos módulos de setup"""
    
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging()
        self.start_time = datetime.now()
        
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
    
    def execute_module(self, module_name: str, module_instance) -> bool:
        """Executa um módulo específico"""
        self.logger.info(f"Iniciando módulo: {module_name}")
        
        try:
            success = module_instance.run()
            if success:
                self.logger.info(f"Módulo {module_name} concluído com sucesso")
            else:
                self.logger.error(f"Módulo {module_name} falhou")
            return success
        except Exception as e:
            self.logger.error(f"Exceção no módulo {module_name}: {e}")
            return False
    
    def run_basic_setup(self) -> bool:
        """Executa setup básico"""
        basic_setup = BasicSetup()
        return basic_setup.run_basic_setup()
    
    def run_hostname_setup(self, hostname: str) -> bool:
        """Executa configuração de hostname"""
        if not hostname:
            return True  # Skip se não fornecido
        hostname_setup = HostnameSetup(hostname)
        return self.execute_module("Hostname", hostname_setup)
    
    def run_docker_setup(self) -> bool:
        """Executa instalação do Docker"""
        docker_setup = DockerSetup(not self.args.no_swarm)
        return self.execute_module("Docker", docker_setup)
    
    def run_traefik_setup(self, email: str) -> bool:
        """Executa instalação do Traefik"""
        if not email:
            # Pergunta email interativamente
            print("\n--- Configuração de SSL/Traefik ---")
            email = self.get_user_input("Digite o email para certificados SSL (Enter para pular)")
            if not email:
                self.logger.warning("Email não fornecido, pulando instalação do Traefik")
                return True
            self.logger.info(f"Email configurado: {email}")
        
        traefik_setup = TraefikSetup(email, self.args.network_name)
        return self.execute_module("Traefik", traefik_setup)
    
    def run_portainer_setup(self, domain: str) -> bool:
        """Executa instalação do Portainer"""
        if not domain:
            # Pergunta domínio interativamente
            print("\n--- Configuração do Portainer ---")
            domain = self.get_user_input("Digite o domínio do Portainer (ex: portainer.seudominio.com, Enter para pular)")
            if not domain:
                self.logger.warning("Domínio não fornecido, pulando instalação do Portainer")
                return True
            self.logger.info(f"Domínio Portainer configurado: {domain}")
        
        portainer_setup = PortainerSetup(domain, self.args.network_name)
        return self.execute_module("Portainer", portainer_setup)
    
    def run_cleanup_setup(self) -> bool:
        """Executa limpeza completa"""
        # Confirmação de segurança
        try:
            print("\n--- ATENÇÃO: LIMPEZA COMPLETA ---")
            print("Esta operação irá remover:")
            print("• Todas as stacks do Docker Swarm")
            print("• Volumes do projeto (vol_certificates, portainer_data)")
            print("• Redes do projeto (orion_network)")
            print("• Sair do Docker Swarm")
            print("• Limpar containers e imagens não utilizadas")
            
            confirm = input("\nDeseja continuar? (digite 'CONFIRMO' para prosseguir): ").strip()
            if confirm != "CONFIRMO":
                self.logger.info("Limpeza cancelada pelo usuário")
                return True
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return True
        
        cleanup_setup = CleanupSetup()
        return self.execute_module("Limpeza", cleanup_setup)
    
    def get_module_map(self) -> dict:
        """Retorna mapeamento de módulos disponíveis"""
        return {
            'basic': ('Setup Básico', lambda: self.run_basic_setup()),
            'hostname': ('Hostname', lambda: self.run_hostname_setup(self.args.hostname)),
            'docker': ('Docker', lambda: self.run_docker_setup()),
            'traefik': ('Traefik', lambda: self.run_traefik_setup(self.args.email)),
            'portainer': ('Portainer', lambda: self.run_portainer_setup(self.args.portainer_domain)),
            'cleanup': ('Limpeza', lambda: self.run_cleanup_setup())
        }
    
    def run_modules(self) -> bool:
        """Executa módulos baseado nos argumentos"""
        module_map = self.get_module_map()
        failed_modules = []
        
        if self.args.module:
            # Executa módulo específico
            if self.args.module in module_map:
                module_name, module_func = module_map[self.args.module]
                success = module_func()
                if not success:
                    failed_modules.append(module_name)
            else:
                self.logger.error(f"Módulo desconhecido: {self.args.module}")
                return False
        else:
            # Executa módulos principais (exceto cleanup)
            main_modules = ['basic', 'hostname', 'docker', 'traefik', 'portainer']
            
            for module_key in main_modules:
                if module_key in module_map:
                    module_name, module_func = module_map[module_key]
                    success = module_func()
                    if not success:
                        failed_modules.append(module_name)
                        if self.args.stop_on_error:
                            self.logger.error(f"Parando execução devido a falha em: {module_name}")
                            break
        
        return len(failed_modules) == 0
    
    def show_summary(self, success: bool) -> None:
        """Exibe resumo da execução"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if success:
            self.logger.info(f"Setup concluído com sucesso ({duration:.2f}s)")
            self.logger.info("Próximas etapas: Portainer, Traefik, aplicações")
        else:
            self.logger.error(f"Setup concluído com falhas ({duration:.2f}s)")
