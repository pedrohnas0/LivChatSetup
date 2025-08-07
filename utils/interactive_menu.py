#!/usr/bin/env python3

import logging
from utils.module_coordinator import ModuleCoordinator

class InteractiveMenu:
    """Menu interativo para seleção de aplicações"""
    
    # Cores do Setup (seguindo padrão do script original)
    AMARELO = "\033[33m"
    VERDE = "\033[32m"
    BRANCO = "\033[97m"
    BEGE = "\033[93m"
    VERMELHO = "\033[91m"
    RESET = "\033[0m"
    
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.coordinator = ModuleCoordinator(args)
        
    def show_menu(self):
        """Exibe o menu principal sem limpar o terminal"""
        print(f"\n{self.BRANCO}## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ##{self.RESET}")
        print(f"{self.BRANCO}##                           {self.VERDE}SETUP LIVCHAT - MENU PRINCIPAL{self.BRANCO}                                     ##{self.RESET}")
        print(f"{self.BRANCO}## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ##{self.RESET}")
        print()
        print(f"{self.BEGE}Escolha a aplicação que deseja instalar:{self.RESET}")
        print()
        print(f"{self.AMARELO}  [1]{self.BRANCO} Configuração Básica do Sistema{self.RESET}")
        print(f"{self.AMARELO}  [2]{self.BRANCO} Configuração de Hostname{self.RESET}")
        print(f"{self.AMARELO}  [3]{self.BRANCO} Instalação do Docker + Swarm{self.RESET}")
        print(f"{self.AMARELO}  [4]{self.BRANCO} Instalação do Traefik (Proxy Reverso){self.RESET}")
        print(f"{self.AMARELO}  [5]{self.BRANCO} Instalação do Portainer (Gerenciador Docker){self.RESET}")
        print()
        print(f"{self.VERDE}  BANCOS DE DADOS:{self.RESET}")
        print(f"{self.AMARELO}  [6]{self.BRANCO} Redis (Cache/Session Store){self.RESET}")
        print(f"{self.AMARELO}  [7]{self.BRANCO} PostgreSQL (Banco Relacional){self.RESET}")
        print(f"{self.AMARELO}  [8]{self.BRANCO} PostgreSQL + PgVector (Banco Vetorial){self.RESET}")
        print()
        print(f"{self.VERDE}  ARMAZENAMENTO:{self.RESET}")
        print(f"{self.AMARELO}  [9]{self.BRANCO} MinIO (S3 Compatible Storage){self.RESET}")
        print()
        print(f"{self.VERDE}  APLICAÇÕES:{self.RESET}")
        print(f"{self.AMARELO} [10]{self.BRANCO} Chatwoot (Customer Support Platform){self.RESET}")
        print(f"{self.AMARELO} [11]{self.BRANCO} N8N (Workflow Automation + Cloudflare DNS){self.RESET}")
        print(f"{self.AMARELO} [12]{self.BRANCO} Grafana (Stack de Monitoramento){self.RESET}")
        print(f"{self.AMARELO} [13]{self.BRANCO} GOWA (WhatsApp API Multi Device){self.RESET}")
        print()
        print(f"{self.VERDE}  UTILITÁRIOS:{self.RESET}")
        print(f"{self.AMARELO} [14]{self.BRANCO} Instalar Tudo (Básico + Docker + Traefik + Portainer){self.RESET}")
        print(f"{self.AMARELO} [15]{self.VERMELHO} Limpeza Completa do Ambiente{self.RESET}")
        print(f"{self.AMARELO}  [0]{self.BEGE} Sair{self.RESET}")
        print()
        print(f"{self.BRANCO}## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ## // ##{self.RESET}")
        
    def get_user_choice(self):
        """Obtém a escolha do usuário"""
        try:
            choice = input(f"{self.AMARELO}Digite sua opção [0-15]: {self.RESET}").strip()
            return choice
        except KeyboardInterrupt:
            print(f"\n{self.VERMELHO}Operação cancelada pelo usuário.{self.RESET}")
            return "0"
    
    def execute_choice(self, choice):
        """Executa a opção escolhida pelo usuário"""
        success = False
        
        if choice == "1":
            print(f"\n{self.VERDE}Executando configuração básica do sistema...{self.RESET}")
            success = self.coordinator.execute_module('basic')
            
        elif choice == "2":
            print(f"\n{self.VERDE}Executando configuração de hostname...{self.RESET}")
            success = self.coordinator.execute_module('hostname')
            
        elif choice == "3":
            print(f"\n{self.VERDE}Executando instalação do Docker...{self.RESET}")
            success = self.coordinator.execute_module('docker')
            
        elif choice == "4":
            print(f"\n{self.VERDE}Executando instalação do Traefik...{self.RESET}")
            email = self.args.email or input(f"{self.AMARELO}Digite seu email para certificados SSL: {self.RESET}")
            success = self.coordinator.execute_module('traefik', email=email)
            
        elif choice == "5":
            print(f"\n{self.VERDE}Executando instalação do Portainer...{self.RESET}")
            domain = self.args.portainer_domain or input(f"{self.AMARELO}Digite o domínio para o Portainer: {self.RESET}")
            success = self.coordinator.execute_module('portainer', portainer_domain=domain)
            
        elif choice == "6":
            print(f"\n{self.VERDE}Executando instalação do Redis...{self.RESET}")
            success = self.coordinator.execute_module('redis')
            
        elif choice == "7":
            print(f"\n{self.VERDE}Executando instalação do PostgreSQL...{self.RESET}")
            success = self.coordinator.execute_module('postgres')
            
        elif choice == "8":
            print(f"\n{self.VERDE}Executando instalação do PostgreSQL + PgVector...{self.RESET}")
            success = self.coordinator.execute_module('pgvector')
            
        elif choice == "9":
            print(f"\n{self.VERDE}Executando instalação do MinIO...{self.RESET}")
            success = self.coordinator.execute_module('minio')
            
        elif choice == "10":
            print(f"\n{self.VERDE}Executando instalação do Chatwoot...{self.RESET}")
            success = self.coordinator.execute_module('chatwoot')
                
        elif choice == "11":
            print(f"\n{self.VERDE}Executando instalação do N8N...{self.RESET}")
            success = self.coordinator.execute_module('n8n')
                
        elif choice == "12":
            print(f"\n{self.VERDE}Executando instalação do Grafana...{self.RESET}")
            success = self.coordinator.execute_module('grafana')
            
        elif choice == "13":
            print(f"\n{self.VERDE}Executando instalação do GOWA...{self.RESET}")
            success = self.coordinator.execute_module('gowa')
            
        elif choice == "14":
            print(f"\n{self.VERDE}Executando instalação completa...{self.RESET}")
            success = self.install_full_stack()
            
        elif choice == "15":
            print(f"\n{self.VERMELHO}Executando limpeza completa...{self.RESET}")
            confirm = input(f"{self.VERMELHO}ATENÇÃO: Isso irá remover TODOS os containers, volumes e redes do Docker Swarm. Confirma? (digite 'CONFIRMO'): {self.RESET}")
            if confirm == 'CONFIRMO':
                success = self.coordinator.execute_module('cleanup')
            else:
                print(f"{self.AMARELO}Limpeza cancelada pelo usuário.{self.RESET}")
                success = True
                
        elif choice == "0":
            print(f"\n{self.BEGE}Saindo do menu...{self.RESET}")
            return False, True
            
        else:
            print(f"\n{self.VERMELHO}Opção '{choice}' inválida. Tente novamente.{self.RESET}")
            return False, False
        
        return success, False
    
    def install_full_stack(self):
        """Instala o stack completo básico"""
        modules = ['basic', 'hostname', 'docker', 'traefik', 'portainer']
        
        print(f"\n{self.AMARELO}=== Instalação Completa do Stack ==={self.RESET}")
        print("Os módulos solicitarão as informações necessárias durante a execução.\n")
        
        for module in modules:
            print(f"{self.BEGE}📋 Executando módulo: {module}{self.RESET}")
            
            success = self.coordinator.execute_module(module)
            
            if not success:
                print(f"{self.VERMELHO}❌ Falha no módulo {module}. Interrompendo instalação.{self.RESET}")
                return False
                
        print(f"\n{self.VERDE}✅ Instalação completa finalizada com sucesso!{self.RESET}")
        return True
    
    def show_result(self, success, module_name=""):
        """Exibe o resultado da operação"""
        if success:
            print(f"\n{self.VERDE}[ OK ] {module_name} instalado com sucesso!{self.RESET}")
        else:
            print(f"\n{self.VERMELHO}[ ERRO ] Falha na instalação do {module_name}{self.RESET}")
        
        print(f"\n{self.BEGE}Pressione Enter para continuar...{self.RESET}")
        input()
    
    def run(self):
        """Executa o menu interativo"""
        print(f"\n{self.VERDE}Bem-vindo ao Setup LivChat!{self.RESET}")
        
        while True:
            self.show_menu()
            choice = self.get_user_choice()
            
            success, should_exit = self.execute_choice(choice)
            
            if should_exit:
                break
                
            if choice != "0":
                self.show_result(success)
        
        print(f"\n{self.VERDE}Obrigado por usar o Setup LivChat!{self.RESET}")
        return True
