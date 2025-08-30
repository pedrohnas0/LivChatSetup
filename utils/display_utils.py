#!/usr/bin/env python3
"""
Utilitários para exibição e formatação visual
Padroniza a renderização de banners, headers e elementos visuais
"""

import sys
from typing import Optional, List

class DisplayUtils:
    """Utilitários para renderização visual padronizada"""
    
    # Cores do Setup (seguindo padrão do projeto)
    AMARELO = "\033[33m"
    VERDE = "\033[32m"
    BRANCO = "\033[97m"
    BEGE = "\033[93m"
    VERMELHO = "\033[91m"
    CINZA = "\033[90m"
    AZUL = "\033[94m"
    RESET = "\033[0m"
    
    @staticmethod
    def render_banner(title: str, subtitle: str = None, width: int = 95) -> None:
        """
        Renderiza banner principal com bordas arredondadas
        
        Args:
            title: Título principal
            subtitle: Subtítulo opcional (ex: "v. 1.0.0")
            width: Largura total do banner
        """
        print(f"\n{DisplayUtils.CINZA}╭{'─' * (width-2)}╮{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        
        # Título centralizado
        title_padding = (width - 2 - len(title)) // 2
        remaining = (width - 2) - title_padding - len(title)
        print(f"{DisplayUtils.CINZA}│{' ' * title_padding}{DisplayUtils.AZUL}{title}{DisplayUtils.RESET}{' ' * remaining}{DisplayUtils.CINZA}│{DisplayUtils.RESET}")
        
        # Subtítulo se fornecido
        if subtitle:
            sub_padding = (width - 2 - len(subtitle)) // 2
            remaining_sub = (width - 2) - sub_padding - len(subtitle)
            print(f"{DisplayUtils.CINZA}│{' ' * sub_padding}{DisplayUtils.BEGE}{subtitle}{DisplayUtils.RESET}{' ' * remaining_sub}{DisplayUtils.CINZA}│{DisplayUtils.RESET}")
        
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}╰{'─' * (width-2)}╯{DisplayUtils.RESET}\n")
    
    @staticmethod
    def render_section_header(title: str, width: int = 80) -> None:
        """
        Renderiza cabeçalho de seção
        
        Args:
            title: Título da seção
            width: Largura do header
        """
        padding = (width - len(title) - 4) // 2
        remaining = width - len(title) - 4 - padding
        header_line = f"╭─ {title} {'─' * padding}{'─' * remaining}╮"
        
        print(f"\n{DisplayUtils.VERDE}{header_line}{DisplayUtils.RESET}")
    
    @staticmethod
    def render_section_footer(width: int = 80) -> None:
        """Renderiza rodapé de seção"""
        print(f"{DisplayUtils.VERDE}╰{'─' * (width-2)}╯{DisplayUtils.RESET}\n")
    
    @staticmethod
    def render_info_box(title: str, items: List[str], width: int = 80) -> None:
        """
        Renderiza caixa de informações
        
        Args:
            title: Título da caixa
            items: Lista de itens para exibir
            width: Largura da caixa
        """
        print(f"\n{DisplayUtils.CINZA}╭─ {title} {'─' * (width - len(title) - 5)}╮{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        
        for item in items:
            item_padding = width - 2 - len(item) - 2
            print(f"{DisplayUtils.CINZA}│ {DisplayUtils.BRANCO}{item}{DisplayUtils.RESET}{' ' * item_padding}{DisplayUtils.CINZA}│{DisplayUtils.RESET}")
        
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}╰{'─' * (width-2)}╯{DisplayUtils.RESET}\n")
    
    @staticmethod
    def render_progress_step(step: str, status: str = "executando") -> None:
        """
        Renderiza passo do progresso
        
        Args:
            step: Descrição do passo
            status: Status (executando, concluido, erro)
        """
        if status == "concluido":
            icon = f"{DisplayUtils.VERDE}✓{DisplayUtils.RESET}"
        elif status == "erro":
            icon = f"{DisplayUtils.VERMELHO}✗{DisplayUtils.RESET}"
        else:
            icon = f"{DisplayUtils.AMARELO}•{DisplayUtils.RESET}"
        
        print(f"{icon} {DisplayUtils.BRANCO}{step}{DisplayUtils.RESET}")
    
    @staticmethod
    def render_confirmation(title: str, items: List[tuple], width: int = 80) -> None:
        """
        Renderiza tela de confirmação
        
        Args:
            title: Título da confirmação
            items: Lista de tuplas (label, value)
            width: Largura da caixa
        """
        print(f"\n{DisplayUtils.AMARELO}╭─ {title} {'─' * (width - len(title) - 5)}╮{DisplayUtils.RESET}")
        print(f"{DisplayUtils.AMARELO}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        
        for label, value in items:
            line = f"{label}: {value}"
            line_padding = width - 2 - len(line) - 2
            print(f"{DisplayUtils.AMARELO}│ {DisplayUtils.BRANCO}{line}{DisplayUtils.RESET}{' ' * line_padding}{DisplayUtils.AMARELO}│{DisplayUtils.RESET}")
        
        print(f"{DisplayUtils.AMARELO}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        print(f"{DisplayUtils.AMARELO}╰{'─' * (width-2)}╯{DisplayUtils.RESET}\n")
    
    @staticmethod
    def render_ascii_logo() -> None:
        """Renderiza logo ASCII do LivChat com banner moderno"""
        logo_lines = [
            "██╗███╗   ██╗██╗ ██████╗██╗ █████╗ ███╗   ██╗██████╗  ██████╗",
            "██║████╗  ██║██║██╔════╝██║██╔══██╗████╗  ██║██╔══██╗██╔═══██╗",
            "██║██╔██╗ ██║██║██║     ██║███████║██╔██╗ ██║██║  ██║██║   ██║",
            "██║██║╚██╗██║██║██║     ██║██╔══██║██║╚██╗██║██║  ██║██║   ██║",
            "██║██║ ╚████║██║╚██████╗██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝",
            "╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝"
        ]
        
        width = 95
        print(f"\n{DisplayUtils.CINZA}╭{'─' * (width-2)}╮{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        
        # Logo centralizado
        for line in logo_lines:
            padding = (width - 2 - len(line)) // 2
            remaining = (width - 2) - padding - len(line)
            print(f"{DisplayUtils.CINZA}│{' ' * padding}{DisplayUtils.AZUL}{line}{DisplayUtils.RESET}{' ' * remaining}{DisplayUtils.CINZA}│{DisplayUtils.RESET}")
        
        # Versão
        version = "v. 1.0.0"
        ver_padding = (width - 2 - len(version)) // 2
        ver_remaining = (width - 2) - ver_padding - len(version)
        print(f"{DisplayUtils.CINZA}│{' ' * ver_padding}{DisplayUtils.BEGE}{version}{DisplayUtils.RESET}{' ' * ver_remaining}{DisplayUtils.CINZA}│{DisplayUtils.RESET}")
        
        print(f"{DisplayUtils.CINZA}│{' ' * (width-2)}│{DisplayUtils.RESET}")
        print(f"{DisplayUtils.CINZA}╰{'─' * (width-2)}╯{DisplayUtils.RESET}\n")
    
    @staticmethod
    def clear_screen() -> None:
        """Limpa a tela de forma compatível"""
        print("\033[2J\033[1;1H", end="")
    
    @staticmethod
    def press_enter_to_continue() -> None:
        """Pausa para o usuário pressionar Enter"""
        input(f"\n{DisplayUtils.BEGE}Pressione Enter para continuar...{DisplayUtils.RESET}")