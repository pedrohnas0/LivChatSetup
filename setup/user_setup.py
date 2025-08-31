#!/usr/bin/env python3
"""
Módulo oculto para gerenciar dados do usuário (primeiro nome, último nome)
Este módulo não tem número no menu mas pode ser usado por outras aplicações
"""

import os
from .base_setup import BaseSetup
from utils.config_manager import ConfigManager

class UserSetup(BaseSetup):
    """Setup de dados do usuário (primeiro/último nome)"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, config_manager: ConfigManager = None):
        super().__init__("Configuração de Dados do Usuário")
        self.config = config_manager or ConfigManager()
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback padrão
    
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
        
        # Aplica cor ao título
        colored_line = centered_clean.replace(clean_title, f"{self.BEGE}{clean_title}{self.RESET}")
        
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        return True  # Este setup não tem pré-requisitos específicos
    
    def get_user_data_suggestions(self) -> dict:
        """Obtém sugestões de dados do usuário baseadas no email configurado"""
        email = self.config.get_user_email()
        
        # Tenta extrair nome do email se disponível
        if email and '@' in email:
            username_part = email.split('@')[0]
            # Remove números e pontos comuns
            clean_name = username_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            
            # Capitaliza cada parte
            parts = clean_name.split()
            if len(parts) >= 2:
                first_name = parts[0].capitalize()
                last_name = ' '.join(parts[1:]).title()
            elif len(parts) == 1:
                first_name = parts[0].capitalize()
                last_name = "User"
            else:
                first_name = "Admin"
                last_name = "User"
        else:
            first_name = "Admin"
            last_name = "User"
        
        return {
            "first_name": first_name,
            "last_name": last_name
        }
    
    def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None, allow_escape: bool = False) -> str:
        """Coleta entrada do usuário com sugestão opcional e suporte ao ESC"""
        try:
            if suggestion:
                if allow_escape:
                    full_prompt = f"{prompt} (Enter para '{suggestion}', outro valor para alterar, ESC para pular)"
                else:
                    full_prompt = f"{prompt} (Enter para '{suggestion}' ou digite outro valor)"
            else:
                full_prompt = prompt
                
            print(f"{self.BEGE}{full_prompt}:{self.RESET}", end=" ")
            
            # Lê entrada character por character para detectar ESC
            import sys, tty, termios
            if sys.stdin.isatty():
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno())
                    
                    # Lê primeiro caractere
                    char = sys.stdin.read(1)
                    
                    # Se for ESC (código 27) e escape é permitido
                    if ord(char) == 27 and allow_escape:
                        print(f"{self.CINZA}[pulado]{self.RESET}")
                        return None
                    
                    # Se for Enter e há sugestão
                    if ord(char) == 13 and suggestion:  # Enter = 13
                        print(f"{self.VERDE}{suggestion}{self.RESET}")
                        return suggestion
                    
                    # Caso contrário, volta para input normal
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    print(char, end="")
                    remaining = input()
                    value = (char + remaining).strip()
                    
                except:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    # Fallback para input normal se der problema
                    value = input().strip()
            else:
                # Se não é TTY (pipe, redirecionamento), usa input normal
                value = input().strip()
                
            # Se não digitou nada e há sugestão, usa a sugestão
            if not value and suggestion:
                return suggestion
                
            if required and not value:
                self.logger.warning("Valor obrigatório não fornecido")
                return None
                
            return value if value else None
            
        except KeyboardInterrupt:
            print(f"\n{self.VERMELHO}Operação cancelada pelo usuário.{self.RESET}")
            return None
    
    def collect_user_data(self, auto_suggestions=True) -> dict:
        """Coleta dados do usuário com sugestões automáticas"""
        if auto_suggestions:
            suggestions = self.get_user_data_suggestions()
        else:
            suggestions = {"first_name": "", "last_name": ""}
        
        self._print_section_box("👤 DADOS DO USUÁRIO")
        
        print(f"{self.BEGE}Configure seus dados pessoais (usado em aplicações que necessitam):{self.RESET}")
        print()
        
        # Primeiro nome
        first_name = self.get_user_input(
            "Primeiro Nome", 
            suggestion=suggestions.get("first_name", ""),
            allow_escape=True
        )
        
        # Se ESC foi pressionado, retorna None
        if first_name is None:
            return None
        
        # Último nome
        last_name = self.get_user_input(
            "Último Nome", 
            suggestion=suggestions.get("last_name", ""),
            allow_escape=True
        )
        
        # Se ESC foi pressionado, retorna None
        if last_name is None:
            return None
        
        return {
            "first_name": first_name.strip() if first_name else "",
            "last_name": last_name.strip() if last_name else ""
        }
    
    def save_user_data(self, user_data: dict):
        """Salva dados do usuário no ConfigManager"""
        self.config.config_data["global"]["first_name"] = user_data.get("first_name", "")
        self.config.config_data["global"]["last_name"] = user_data.get("last_name", "")
        self.config.save_config()
        
        self.logger.info("Dados do usuário salvos no ConfigManager")
    
    def get_user_data(self) -> dict:
        """Obtém dados do usuário do ConfigManager"""
        return {
            "first_name": self.config.config_data["global"].get("first_name", ""),
            "last_name": self.config.config_data["global"].get("last_name", "")
        }
    
    def has_user_data(self) -> bool:
        """Verifica se há dados do usuário configurados"""
        user_data = self.get_user_data()
        return bool(user_data.get("first_name") or user_data.get("last_name"))
    
    def run(self) -> bool:
        """Executa configuração dos dados do usuário"""
        self.logger.info("Iniciando configuração de dados do usuário")
        
        user_data = self.collect_user_data()
        if user_data is None:
            self.logger.info("Configuração de dados do usuário cancelada pelo usuário")
            return False
        
        if user_data.get("first_name") or user_data.get("last_name"):
            self.save_user_data(user_data)
            self.logger.info("Dados do usuário configurados com sucesso")
            return True
        else:
            self.logger.info("Nenhum dado de usuário fornecido")
            return False


if __name__ == "__main__":
    import sys
    
    user_setup = UserSetup()
    
    if user_setup.run():
        print("Dados do usuário configurados com sucesso!")
    else:
        print("Configuração de dados do usuário cancelada ou falhou")
        sys.exit(1)