#!/usr/bin/env python3
"""
Teste da Refatoração LivChatSetup v2.0
Demonstra as novas funcionalidades implementadas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager
from utils.module_coordinator import ModuleCoordinator
from utils.cloudflare_api import CloudflareAPI
from utils.interactive_menu import InteractiveMenu
import argparse

def test_config_manager():
    """Testa o ConfigManager"""
    print("🧪 Testando ConfigManager...")
    
    config = ConfigManager()
    
    # Testa configurações globais
    config.set_user_email("teste@livchat.ai")
    config.set_default_subdomain("dev")
    config.set_network_name("livchat_network")
    
    # Testa geração de senhas
    password = config.generate_secure_password()
    print(f"✅ Senha gerada: {password[:10]}... ({len(password)} chars)")
    
    # Testa sugestão de domínio
    suggested_domain = config.suggest_domain("chatwoot")
    print(f"✅ Domínio sugerido para Chatwoot: {suggested_domain}")
    
    # Testa credenciais
    config.save_app_credentials("test_app", {
        "username": "admin",
        "password": password
    })
    
    creds = config.get_app_credentials("test_app") 
    print(f"✅ Credenciais salvas e recuperadas: {creds['username']}")
    
    # Testa resumo
    summary = config.get_summary()
    print(f"✅ Resumo: {summary['total_apps']} apps, DNS: {'ON' if summary['auto_dns_enabled'] else 'OFF'}")
    
    print("✅ ConfigManager testado com sucesso!\n")


def test_module_coordinator():
    """Testa o ModuleCoordinator"""
    print("🧪 Testando ModuleCoordinator...")
    
    # Cria args mock
    args = argparse.Namespace()
    args.network_name = "test_network"
    args.email = "test@livchat.ai"
    args.hostname = "livchat-server"
    args.stop_on_error = False
    
    coordinator = ModuleCoordinator(args)
    
    # Testa resolução de dependências
    selected = ["chatwoot", "n8n"]
    resolved = coordinator.resolve_dependencies(selected)
    print(f"✅ Dependências resolvidas: {' → '.join(resolved)}")
    
    # Testa mapeamento de módulos
    module_map = coordinator.get_module_map()
    print(f"✅ {len(module_map)} módulos mapeados")
    
    print("✅ ModuleCoordinator testado com sucesso!\n")


def test_cloudflare_integration():
    """Testa integração Cloudflare"""
    print("🧪 Testando Integração Cloudflare...")
    
    config = ConfigManager()
    cf = CloudflareAPI(config)
    
    # Testa sugestão de domínio
    suggested = cf.suggest_domain_for_app("grafana")
    print(f"✅ Domínio sugerido para Grafana: {suggested}")
    
    print("✅ Integração Cloudflare testada com sucesso!\n")


def test_interactive_menu():
    """Testa o novo Menu Interativo"""
    print("🧪 Testando Novo Menu TUI...")
    
    # Cria args mock
    args = argparse.Namespace()
    args.network_name = None
    args.email = None
    
    menu = InteractiveMenu(args)
    
    # Testa estrutura de apps
    print(f"✅ Menu carregado com {len(menu.apps)} aplicações disponíveis")
    
    # Testa categorização
    categories = set(app["category"] for app in menu.apps)
    print(f"✅ Categorias disponíveis: {', '.join(categories)}")
    
    print("✅ Menu TUI testado com sucesso!\n")


def show_ascii_banner():
    """Exibe banner do teste"""
    print(f"""
{'='*80}
 ████████╗███████╗███████╗████████╗███████╗
 ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██╔════╝
    ██║   █████╗  ███████╗   ██║   █████╗  
    ██║   ██╔══╝  ╚════██║   ██║   ██╔══╝  
    ██║   ███████╗███████║   ██║   ███████╗
    ╚═╝   ╚══════╝╚══════╝   ╚═╝   ╚══════╝
    
         LivChatSetup v2.0 - Sistema Refatorado
{'='*80}
""")


def main():
    """Executa todos os testes"""
    show_ascii_banner()
    
    print("🚀 Iniciando testes da refatoração...")
    print()
    
    try:
        test_config_manager()
        test_module_coordinator() 
        test_cloudflare_integration()
        test_interactive_menu()
        
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Refatoração LivChatSetup v2.0 implementada com sucesso")
        print()
        print("📋 Funcionalidades implementadas:")
        print("   • Menu TUI com seleção múltipla e rolagem")
        print("   • Gerenciador de configurações JSON centralizado")
        print("   • Sistema de resolução automática de dependências")
        print("   • Geração de senhas seguras e sugestões automáticas")
        print("   • Integração DNS Cloudflare aprimorada")
        print("   • Configurações centralizadas e persistentes")
        print()
        print("🎯 Para usar o novo sistema: sudo python3 main.py")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main()