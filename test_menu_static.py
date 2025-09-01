#!/usr/bin/env python3
"""
Teste estático do menu com dados reais
"""

import sys
import time
import argparse

# Adicionar path para imports
sys.path.insert(0, '/root/CascadeProjects/LivChatSetup')

from utils.interactive_menu import InteractiveMenu

def test_static():
    """Teste estático do menu"""
    # Simular argumentos
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    
    # Criar menu
    print("\033[32mTeste do Menu com Monitoramento Real\033[0m")
    print("\033[93mAguardando inicialização do monitor Docker...\033[0m\n")
    
    menu = InteractiveMenu(args)
    
    # Aguardar coleta de dados
    time.sleep(2)
    
    # Simular algumas seleções
    menu.selected_items = {"traefik", "portainer", "redis", "postgres"}
    menu.selected_index = 6  # PostgreSQL
    
    # Desenhar menu uma vez
    menu.draw_menu(first_draw=True)
    
    # Mostrar status coletado
    print("\n\033[93mStatus dos Serviços Detectados:\033[0m")
    
    if menu.monitor_enabled and menu.docker_monitor:
        services = menu.docker_monitor.get_all_services()
        for service_id, info in services.items():
            if info['status'] == 'running':
                status_color = "\033[32m"  # Verde
            elif info['status'] == 'stopped':
                status_color = "\033[91m"  # Vermelho
            else:
                status_color = "\033[90m"  # Cinza
            
            status = info['status'] or 'not installed'
            replicas = info['replicas'] or '-'
            cpu = f"{info['cpu']:.1f}%" if info['cpu'] else '-'
            mem = f"{info['mem']}M" if info['mem'] else '-'
            
            print(f"{service_id:15} {status_color}Status: {status:12}\033[0m Replicas: {replicas:6} CPU: {cpu:7} MEM: {mem:7}")
    else:
        print("Monitor Docker não disponível")
    
    # Parar monitor
    if menu.docker_monitor:
        menu.docker_monitor.stop_monitoring()
    
    print("\n\033[32mTeste concluído!\033[0m")

if __name__ == "__main__":
    test_static()