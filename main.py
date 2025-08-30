#!/usr/bin/env python3
"""
Sistema de Setup Modular
Sempre inicia pelo menu interativo
"""

import os
import sys
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

def run_setup() -> bool:
    """Executa o menu interativo"""
    logger = setup_logging()
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
    # Valida pré-requisitos
    if not validate_prerequisites():
        sys.exit(1)
    
    try:
        success = run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
