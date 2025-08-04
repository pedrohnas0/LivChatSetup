#!/usr/bin/env python3

import logging
from utils.module_coordinator import ModuleCoordinator

class InteractiveMenu:
    """Menu interativo para seleção de aplicações"""
    
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.coordinator = ModuleCoordinator(args)
        
    def show_menu(self):
        """Exibe o menu principal sem limpar o terminal"""
        print("\n" + "="*60)
        print("           SETUP LIVCHAT - MENU DE APLICAÇÕES")
        print("="*60)
        print()
        print("Escolha a aplicação que deseja instalar:")
        print()
        print("  [1] Configuração Básica do Sistema")
        print("  [2] Configuração de Hostname")
        print("  [3] Instalação do Docker + Swarm")
        print("  [4] Instalação do Traefik (Proxy Reverso)")
        print("  [5] Instalação do Portainer (Gerenciador Docker)")
        print()
        print("  BANCOS DE DADOS:")
        print("  [6] Redis (Cache/Session Store)")
        print("  [7] PostgreSQL (Banco Relacional)")
        print("  [8] PostgreSQL + PgVector (Banco Vetorial)")
        print()
        print("  ARMAZENAMENTO:")
        print("  [9] MinIO (S3 Compatible Storage)")
        print()
        print("  UTILITÁRIOS:")
        print("  [10] Instalar Tudo (Básico + Docker + Traefik + Portainer)")
        print("  [11] Limpeza Completa do Ambiente")
        print("  [0] Sair")
        print()
        print("="*60)
        
    def get_user_choice(self):
        """Obtém a escolha do usuário"""
        try:
            choice = input("Digite sua opção [0-11]: ").strip()
            return choice
        except KeyboardInterrupt:
            print("\nOperação cancelada pelo usuário.")
            return "0"
    
    def execute_choice(self, choice):
        """Executa a opção escolhida pelo usuário"""
        success = False
        
        if choice == "1":
            print("\n🔧 Executando configuração básica do sistema...")
            success = self.coordinator.execute_module('basic')
            
        elif choice == "2":
            print("\n🏷️  Executando configuração de hostname...")
            success = self.coordinator.execute_module('hostname')
            
        elif choice == "3":
            print("\n🐳 Executando instalação do Docker...")
            success = self.coordinator.execute_module('docker')
            
        elif choice == "4":
            print("\n🌐 Executando instalação do Traefik...")
            email = self.args.email or input("Digite seu email para certificados SSL: ")
            success = self.coordinator.execute_module('traefik', email=email)
            
        elif choice == "5":
            print("\n📊 Executando instalação do Portainer...")
            domain = self.args.portainer_domain or input("Digite o domínio para o Portainer: ")
            success = self.coordinator.execute_module('portainer', portainer_domain=domain)
            
        elif choice == "6":
            print("\n🔴 Executando instalação do Redis...")
            success = self.coordinator.execute_module('redis')
            
        elif choice == "7":
            print("\n🐘 Executando instalação do PostgreSQL...")
            success = self.coordinator.execute_module('postgres')
            
        elif choice == "8":
            print("\n🔍 Executando instalação do PostgreSQL + PgVector...")
            success = self.coordinator.execute_module('pgvector')
            
        elif choice == "9":
            print("\n📦 Executando instalação do MinIO...")
            success = self.coordinator.execute_module('minio')
            
        elif choice == "10":
            print("\n🚀 Executando instalação completa...")
            success = self.install_full_stack()
            
        elif choice == "11":
            print("\n🧹 Executando limpeza completa...")
            confirm = input("ATENÇÃO: Isso irá remover TODOS os containers, volumes e redes do Docker Swarm. Confirma? (digite 'CONFIRMO'): ")
            if confirm == 'CONFIRMO':
                success = self.coordinator.execute_module('cleanup')
            else:
                print("Limpeza cancelada pelo usuário.")
                success = True
                
        elif choice == "0":
            print("\nSaindo do menu...")
            return False, True
            
        else:
            print(f"\nOpção '{choice}' inválida. Tente novamente.")
            return False, False
        
        return success, False
    
    def install_full_stack(self):
        """Instala o stack completo básico"""
        modules = ['basic', 'hostname', 'docker', 'traefik', 'portainer']
        
        for module in modules:
            print(f"\n📋 Executando módulo: {module}")
            
            if module == 'traefik':
                email = self.args.email or input("Digite seu email para certificados SSL: ")
                success = self.coordinator.execute_module(module, email=email)
            elif module == 'portainer':
                domain = self.args.portainer_domain or input("Digite o domínio para o Portainer: ")
                success = self.coordinator.execute_module(module, portainer_domain=domain)
            else:
                success = self.coordinator.execute_module(module)
            
            if not success:
                print(f"❌ Falha no módulo {module}. Interrompendo instalação.")
                return False
                
        print("\n✅ Instalação completa finalizada com sucesso!")
        return True
    
    def show_result(self, success, module_name=""):
        """Exibe o resultado da operação"""
        if success:
            print(f"\n✅ {module_name} instalado com sucesso!")
        else:
            print(f"\n❌ Falha na instalação do {module_name}")
        
        print("\nPressione Enter para continuar...")
        input()
    
    def run(self):
        """Executa o menu interativo"""
        print("\n🚀 Bem-vindo ao Setup LivChat!")
        
        while True:
            self.show_menu()
            choice = self.get_user_choice()
            
            success, should_exit = self.execute_choice(choice)
            
            if should_exit:
                break
                
            if choice != "0":
                self.show_result(success)
        
        print("\n👋 Obrigado por usar o Setup LivChat!")
        return True
