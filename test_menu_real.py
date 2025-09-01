#!/usr/bin/env python3
"""
Teste do menu interativo com monitoramento real
"""

import sys
import argparse

# Adicionar path para imports
sys.path.insert(0, '/root/CascadeProjects/LivChatSetup')

from utils.interactive_menu import InteractiveMenu

def main():
    # Simular argumentos
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Modo verbose')
    parser.add_argument('--quiet', action='store_true', help='Modo quiet')
    args = parser.parse_args()
    
    # Criar e executar menu
    menu = InteractiveMenu(args)
    
    # Testar apenas o menu TUI
    selected = menu.run_tui_menu()
    
    if selected:
        print(f"\nSelecionados: {selected}")
    else:
        print("\nNenhuma seleção feita")

if __name__ == "__main__":
    main()