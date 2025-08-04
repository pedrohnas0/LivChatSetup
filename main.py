#!/usr/bin/env python3
"""
Sistema de Setup Modular
Coordenador principal que executa todos os módulos de setup
"""

import os
import sys
import argparse
import subprocess

# Instala dependências automaticamente
def install_dependencies():
    """Instala dependências necessárias"""
    try:
        import jinja2
    except ImportError:
        print("Instalando Jinja2...")
        subprocess.run([sys.executable, "-m", "pip", "install", "jinja2"], check=True)
        print("Jinja2 instalado com sucesso")

# Instala dependências no início
install_dependencies()

# Importa coordenador de módulos
from utils.module_coordinator import ModuleCoordinator
from utils.interactive_menu import InteractiveMenu

class MainSetup:
    """Coordenador principal simplificado"""
    
    def __init__(self, args):
        self.args = args
        self.coordinator = ModuleCoordinator(args)
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos básicos"""
        # Verifica privilégios root
        if os.geteuid() != 0:
            print("Este script deve ser executado como root")
            print("Execute: sudo python3 main.py")
            return False
        
        # Valida hostname apenas se não for cleanup e não for interativo
        if (not self.args.hostname and 
            self.args.module != 'cleanup' and 
            not self.args.interactive and
            not self.args.menu):
            print("Nome do servidor não fornecido. Use --hostname ou --interactive")
            return False
            
        return True
    
    def run_setup(self):
        """Executa o setup com base nos argumentos fornecidos"""
        # Se menu interativo foi solicitado
        if self.args.menu:
            menu = InteractiveMenu(self.args)
            return menu.run()
        
        self.logger.info("Iniciando setup do sistema")
        
        # Delega execução para o coordenador
        coordinator = ModuleCoordinator(self.args)
        success = coordinator.run_modules()
        
        if success:
            self.logger.info("Setup concluído com sucesso")
        else:
            self.logger.error("Setup falhou")
            
        return success

    def run(self) -> bool:
        """Executa o setup principal"""
        if not self.validate_prerequisites():
            return False
        
        # Delega toda a execução para o coordenador
        success = self.run_setup()
        self.coordinator.show_summary(success)
        
        return success

def parse_arguments():
    """Parse dos argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Sistema de Setup Modular para Servidores Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  sudo python3 main.py --hostname meuservidor --email admin@dominio.com --portainer-domain portainer.dominio.com
  sudo python3 main.py --interactive
  sudo python3 main.py --hostname srv01 --module docker
  sudo python3 main.py --hostname srv01 --email ssl@dominio.com --module traefik
  sudo python3 main.py --hostname srv01 --portainer-domain portainer.dominio.com --module portainer
        """
    )
    
    parser.add_argument(
        "--hostname",
        help="Nome do servidor (hostname)"
    )
    
    parser.add_argument(
        "--email",
        help="Email para certificados SSL do Traefik"
    )
    
    parser.add_argument('--portainer-domain', type=str, help='Domínio para o Portainer')
    parser.add_argument('--network-name', type=str, default='orion_network', help='Nome da rede Docker')
    parser.add_argument('--menu', action='store_true', help='Executa o menu interativo')
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Modo interativo (pergunta as informações)"
    )
    
    parser.add_argument(
        "--module", "-m",
        choices=["basic", "hostname", "docker", "traefik", "portainer", "network", "cleanup"],
        help="Executa apenas um módulo específico"
    )
    
    parser.add_argument(
        "--no-swarm",
        action="store_true",
        help="Instala Docker sem inicializar Swarm"
    )
    
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Para execução no primeiro erro"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilita logs de debug"
    )
    
    return parser.parse_args()

def main():
    """Função principal"""
    args = parse_arguments()
    
    # Configura nível de log se debug
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Executa setup
    setup = MainSetup(args)
    
    try:
        success = setup.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
