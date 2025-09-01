#!/usr/bin/env python3
"""
Módulo de Configuração SMTP
Centraliza configurações de email para todos os serviços
Baseado no padrão do PortainerSetup
"""

import re
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup.base_setup import BaseSetup
from utils.config_manager import ConfigManager

class SMTPSetup(BaseSetup):
    """Setup de Configuração SMTP Centralizada"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, config_manager: ConfigManager = None):
        super().__init__("Configuração SMTP")
        self.config = config_manager or ConfigManager()
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos básicos"""
        return True  # SMTP não tem pré-requisitos específicos
    
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
        
        # Centralização perfeita usando Python nativo
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
            
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
    
    def validate_email(self, email: str) -> bool:
        """Valida formato básico de email"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_port(self, port: str) -> bool:
        """Valida se porta é um número válido"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    def detect_ssl_from_port(self, port: str) -> str:
        """Detecta configuração SSL baseada na porta"""
        if port == "465":
            return "true"
        elif port == "587":
            return "false"
        else:
            return "false"  # Padrão
    
    def get_smtp_config_from_user(self) -> dict:
        """Coleta configurações SMTP do usuário com validação"""
        self._print_section_box("📧 CONFIGURAÇÃO SMTP")
        
        # 1. Servidor SMTP
        print(f"\n{self.BEGE}🖥️ SERVIDOR SMTP:{self.RESET}")
        while True:
            smtp_host = self.get_user_input("Servidor SMTP", 
                                           suggestion="smtp-relay.brevo.com", 
                                           required=True)
            if smtp_host:
                break
            print(f"{self.VERMELHO}❌ Servidor SMTP é obrigatório!{self.RESET}")
        
        # 2. Porta SMTP com validação
        print(f"\n{self.BEGE}🔌 PORTA E SEGURANÇA:{self.RESET}")
        while True:
            smtp_port = self.get_user_input("Porta SMTP", suggestion="587")
            if self.validate_port(smtp_port):
                break
            print(f"{self.VERMELHO}❌ Porta deve ser um número entre 1 e 65535!{self.RESET}")
        
        # Auto-detectar SSL baseado na porta
        smtp_ssl = self.detect_ssl_from_port(smtp_port)
        ssl_status = "SSL/TLS" if smtp_ssl == "true" else "STARTTLS"
        print(f"{self.CINZA}   → Segurança detectada: {ssl_status} (porta {smtp_port}){self.RESET}")
        
        # 3. Autenticação SMTP
        print(f"\n{self.BEGE}👤 AUTENTICAÇÃO:{self.RESET}")
        print(f"{self.CINZA}   Exemplo Brevo: 7ce2eb001@smtp-brevo.com{self.RESET}")
        while True:
            smtp_username = self.get_user_input("Usuário/Email de autenticação SMTP", required=True)
            if smtp_username:
                break
            print(f"{self.VERMELHO}❌ Usuário de autenticação é obrigatório!{self.RESET}")
        
        while True:
            smtp_password = self.get_user_input("Senha SMTP", required=True)
            if smtp_password:
                break
            print(f"{self.VERMELHO}❌ Senha SMTP é obrigatória!{self.RESET}")
        
        # 4. Email remetente (pode ser diferente do usuário de auth)
        print(f"\n{self.BEGE}📨 REMETENTE:{self.RESET}")
        print(f"{self.CINZA}   Exemplo: contato@meudominio.com{self.RESET}")
        while True:
            sender_email = self.get_user_input("Email remetente (FROM)", required=True)
            if sender_email and self.validate_email(sender_email):
                break
            print(f"{self.VERMELHO}❌ Email remetente deve ser um email válido!{self.RESET}")
        
        # 5. Nome do remetente (opcional)
        sender_name = self.get_user_input("Nome do remetente", 
                                         suggestion="Sistema LivChat")
        if not sender_name:
            sender_name = "Sistema LivChat"
        
        # 6. Domínio SMTP (extraído do email)
        smtp_domain = sender_email.split("@")[1] if "@" in sender_email else ""
        
        return {
            'smtp_host': smtp_host,
            'smtp_port': int(smtp_port),
            'smtp_ssl': smtp_ssl,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'sender_email': sender_email,
            'sender_name': sender_name,
            'smtp_domain': smtp_domain
        }
    
    def show_config_confirmation(self, config: dict) -> bool:
        """Exibe configurações para confirmação"""
        self._print_section_box("📋 CONFIRMAÇÃO DAS CONFIGURAÇÕES SMTP")
        
        print(f"{self.VERDE}🖥️{self.RESET} Servidor: {self.BRANCO}{config['smtp_host']}:{config['smtp_port']}{self.RESET}")
        
        ssl_method = "SSL/TLS" if config['smtp_ssl'] == "true" else "STARTTLS"
        print(f"{self.VERDE}🔒{self.RESET} Segurança: {self.BRANCO}{ssl_method}{self.RESET}")
        
        print(f"{self.VERDE}👤{self.RESET} Usuário: {self.BRANCO}{config['smtp_username']}{self.RESET}")
        print(f"{self.VERDE}🔑{self.RESET} Senha: {self.BRANCO}[{'*' * len(config['smtp_password'])}]{self.RESET}")
        
        print(f"{self.VERDE}📨{self.RESET} Email remetente: {self.BRANCO}{config['sender_email']}{self.RESET}")
        print(f"{self.VERDE}📝{self.RESET} Nome remetente: {self.BRANCO}{config['sender_name']}{self.RESET}")
        
        if config['smtp_domain']:
            print(f"{self.VERDE}🌐{self.RESET} Domínio: {self.BRANCO}{config['smtp_domain']}{self.RESET}")
        
        print()
        print(f"{self.BEGE}Pressione {self.VERDE}Enter{self.BEGE} para confirmar · {self.VERMELHO}Esc{self.BEGE} para corrigir dados{self.RESET}")
        
        try:
            import termios
            import tty
            import sys
            
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            try:
                tty.setcbreak(sys.stdin.fileno())
                while True:
                    key = sys.stdin.read(1)
                    
                    if ord(key) == 10 or ord(key) == 13:  # Enter
                        print("✅ Configurações confirmadas!")
                        return True
                    elif ord(key) == 27:  # Esc
                        print("❌ Voltando para corrigir dados...")
                        return False
                    elif key.lower() == 'q':  # Q para quit
                        print("❌ Configuração cancelada")
                        return False
                        
            finally:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
                
        except ImportError:
            # Fallback para sistemas sem termios
            confirm = input("Confirmar? (Enter=Sim, N=Não): ").strip()
            return not confirm or confirm.lower() in ['', 'sim', 's', 'yes', 'y']
    
    def save_smtp_config(self, config: dict) -> bool:
        """Salva configuração SMTP no ConfigManager"""
        try:
            # Salva no ConfigManager para reutilização
            self.config.save_app_config("smtp", {
                "smtp_host": config['smtp_host'],
                "smtp_port": config['smtp_port'],
                "smtp_ssl": config['smtp_ssl'],
                "smtp_username": config['smtp_username'],
                "smtp_password": config['smtp_password'],
                "sender_email": config['sender_email'],
                "sender_name": config['sender_name'],
                "smtp_domain": config['smtp_domain'],
                "configured": True
            })
            
            self.logger.info("✅ Configuração SMTP salva no sistema")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração SMTP: {e}")
            return False
    
    def is_smtp_configured(self) -> bool:
        """Verifica se SMTP já está configurado"""
        smtp_config = self.config.get_app_config("smtp")
        return smtp_config and smtp_config.get("configured", False)
    
    def get_smtp_config(self) -> dict:
        """Obtém configuração SMTP salva"""
        return self.config.get_app_config("smtp") or {}
    
    def show_success_summary(self, config: dict):
        """Exibe resumo de sucesso"""
        self._print_section_box("✅ SMTP CONFIGURADO COM SUCESSO!")
        
        print(f"{self.VERDE}📧{self.RESET} SMTP configurado e pronto para uso")
        print(f"{self.VERDE}🖥️{self.RESET} Servidor: {config['smtp_host']}:{config['smtp_port']}")
        print(f"{self.VERDE}📨{self.RESET} Remetente: {config['sender_name']} <{config['sender_email']}>")
        print()
        print(f"{self.BEGE}ℹ️  Esta configuração será reutilizada automaticamente por:{self.RESET}")
        print(f"   {self.VERDE}•{self.RESET} N8N (Workflow Automation)")
        print(f"   {self.VERDE}•{self.RESET} Chatwoot (Customer Support)")
        print(f"   {self.VERDE}•{self.RESET} Passbolt (Password Manager)")
        print(f"   {self.VERDE}•{self.RESET} Outros serviços que precisem de email")
        print()
        
    def run(self) -> bool:
        """Executa a configuração SMTP"""
        self.log_step_start("Configuração SMTP")
        
        if not self.validate_prerequisites():
            return False
        
        # Verifica se já está configurado
        if self.is_smtp_configured():
            existing_config = self.get_smtp_config()
            self.logger.info("SMTP já está configurado - pulando configuração")
            self.log_step_complete("Configuração SMTP")
            return True
        
        # Loop de coleta e confirmação de configurações
        while True:
            # Coleta configurações do usuário
            config = self.get_smtp_config_from_user()
            if not config:
                self.logger.error("Falha ao coletar configurações SMTP")
                return False
            
            # Confirma configurações
            confirmation = self.show_config_confirmation(config)
            if confirmation:
                break  # Confirmado, sair do loop
            else:
                # Usuário quer corrigir dados, voltar ao início do loop
                print(f"\n{self.BEGE}Vamos corrigir os dados SMTP...{self.RESET}")
                continue
        
        # Salva configurações
        if not self.save_smtp_config(config):
            return False
        
        # Exibe resumo de sucesso
        self.show_success_summary(config)
        
        duration = self.get_duration()
        self.logger.info(f"Configuração SMTP concluída ({duration:.2f}s)")
        self.log_step_complete("Configuração SMTP")
        
        return True

def main():
    """Função principal para teste do módulo"""
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    setup = SMTPSetup()
    
    if setup.run():
        print("Configuração SMTP concluída com sucesso")
    else:
        print("Falha na configuração SMTP")
        sys.exit(1)

if __name__ == "__main__":
    main()