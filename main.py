#!/usr/bin/env python3
"""
Sistema de Setup Modular
Sempre inicia pelo menu interativo
"""

import os
import sys
import subprocess
import argparse

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

# Importa menu interativo
from utils.interactive_menu import InteractiveMenu
from config import setup_logging

def validate_prerequisites() -> bool:
    """Valida pré-requisitos básicos"""
    # Verifica privilégios root
    if os.geteuid() != 0:
        print("Este script deve ser executado como root")
        print("Execute: sudo python3 main.py")
        return False
    
    return True

def run_setup(log_level='CRITICAL') -> bool:
    """Executa o menu interativo"""
    logger = setup_logging(log_level)
    if log_level in ['DEBUG', 'INFO']:  # Só mostra se for modo verbose
        logger.info("Iniciando sistema de setup - Menu Interativo")
    
    # Cria objeto args vazio para compatibilidade
    class EmptyArgs:
        def __init__(self):
            self.hostname = None
            self.email = None
            self.portainer_domain = None
            self.network_name = None
            self.menu = True
            self.interactive = True
            self.module = None
            self.no_swarm = False
            self.stop_on_error = False
            self.debug = False
    
    # Sempre executa o menu interativo
    menu = InteractiveMenu(EmptyArgs())
    return menu.run()

def main():
    """Função principal - sempre inicia pelo menu interativo"""
    parser = argparse.ArgumentParser(
        description='Sistema de Setup LivChat',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos de log disponíveis:
  (padrão)     Sem logs no console (silencioso)
  --quiet      Mostra apenas ERROR e CRITICAL  
  --verbose    Mostra todos os logs (DEBUG)
        """
    )
    
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso - apenas erros críticos'
    )
    log_group.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Modo detalhado - todos os logs'
    )
    
    args = parser.parse_args()
    
    # Define nível de log baseado nos argumentos
    if args.quiet:
        log_level = 'ERROR'
    elif args.verbose:
        log_level = 'DEBUG'
    else:
        log_level = 'CRITICAL'  # Padrão - sem logs no console
    
    # Valida pré-requisitos
    if not validate_prerequisites():
        sys.exit(1)
    
    try:
        success = run_setup(log_level)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
