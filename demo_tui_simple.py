#!/usr/bin/env python3
"""
Demo TUI Menu simples para LivChatSetup
Seguindo o padrão visual do projeto (cores ANSI, sem limpeza de tela)
"""

import sys
import termios
import tty
import time

class SimpleTUIMenu:
    # Cores do Setup (seguindo padrão do projeto)
    AMARELO = "\033[33m"
    VERDE = "\033[32m"
    BRANCO = "\033[97m"
    BEGE = "\033[93m"
    VERMELHO = "\033[91m"
    CINZA = "\033[90m"  # Para itens não focados
    RESET = "\033[0m"
    
    def __init__(self):
        self.selected_index = 0
        self.selected_items = set()
        
        # Lista expandida até 35 itens
        self.apps = [
            {"id": 1, "name": "Configuração Básica do Sistema"},
            {"id": 2, "name": "Configuração de Hostname"},
            {"id": 3, "name": "Instalação do Docker + Swarm"},
            {"id": 4, "name": "Instalação do Traefik (Proxy Reverso)"},
            {"id": 5, "name": "Instalação do Portainer (Gerenciador Docker)"},
            {"id": 6, "name": "Redis (Cache/Session Store)"},
            {"id": 7, "name": "PostgreSQL (Banco Relacional)"},
            {"id": 8, "name": "PostgreSQL + PgVector (Banco Vetorial)"},
            {"id": 9, "name": "MinIO (S3 Compatible Storage)"},
            {"id": 10, "name": "Chatwoot (Customer Support Platform)"},
            {"id": 11, "name": "Directus (Headless CMS)"},
            {"id": 12, "name": "N8N (Workflow Automation)"},
            {"id": 13, "name": "Grafana (Stack de Monitoramento)"},
            {"id": 14, "name": "GOWA (WhatsApp API Multi Device)"},
            {"id": 15, "name": "LivChatBridge (Webhook Connector)"},
            {"id": 16, "name": "Instalar Tudo (Stack Completo)"},
            {"id": 17, "name": "Limpeza Completa do Ambiente"},
            {"id": 18, "name": "Passbolt (Password Manager)"},
            {"id": 19, "name": "Evolution API v2 (WhatsApp API)"},
            {"id": 20, "name": "Em breve"},
            {"id": 21, "name": "Em breve"},
            {"id": 22, "name": "Em breve"},
            {"id": 23, "name": "Em breve"},
            {"id": 24, "name": "Em breve"},
            {"id": 25, "name": "Em breve"},
            {"id": 26, "name": "Em breve"},
            {"id": 27, "name": "Em breve"},
            {"id": 28, "name": "Em breve"},
            {"id": 29, "name": "Em breve"},
            {"id": 30, "name": "Em breve"},
            {"id": 31, "name": "Em breve"},
            {"id": 32, "name": "Em breve"},
            {"id": 33, "name": "Em breve"},
            {"id": 34, "name": "Em breve"},
            {"id": 35, "name": "Em breve"},
        ]
        
        # Para controle de terminal não-bloqueante
        self.old_settings = None
        
        # Para controle de enter duplo (boas práticas: 500ms)
        self.last_enter_time = 0
        self.double_click_threshold = 0.5  # 500ms - padrão de sistemas
        
    def setup_terminal(self):
        """Configura terminal para entrada não-bloqueante"""
        self.old_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        
    def restore_terminal(self):
        """Restaura configurações originais do terminal"""
        if self.old_settings:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_settings)
    
    def get_key(self):
        """Lê uma tecla (bloqueante)"""
        key = sys.stdin.read(1)
        
        # Detectar setas (sequências escape)
        if key == '\x1b':  # ESC
            # Ler próximos caracteres para setas
            try:
                key2 = sys.stdin.read(1)
                if key2 == '[':
                    key3 = sys.stdin.read(1)
                    if key3 == 'A':  # Seta cima
                        return 'UP'
                    elif key3 == 'B':  # Seta baixo
                        return 'DOWN'
                    elif key3 == 'C':  # Seta direita
                        return 'RIGHT'
                    elif key3 == 'D':  # Seta esquerda
                        return 'LEFT'
                    elif key3 == 'Z':  # Shift+Tab
                        return 'SHIFT_TAB'
                else:
                    # ESC puro
                    return 'ESC'
            except:
                return 'ESC'
        
        # Detectar caracteres especiais
        if ord(key) == 1:  # Ctrl+A
            return 'CTRL_A'
        elif ord(key) == 9:  # Tab
            return 'TAB'
        elif ord(key) == 10:  # Enter (LF)
            return 'ENTER'
        elif ord(key) == 13:  # Enter (CR)
            return 'ENTER'
            
        return key
    
    def draw_menu(self, first_draw=False):
        """Desenha o menu inline (sem limpar tela)"""
        # Construir todo o menu em memória primeiro
        lines = []
        
        if first_draw:
            lines.append("")  # linha vazia inicial
        
        # Header com contador mais harmonioso
        selected_count = len(self.selected_items)
        total_count = len(self.apps)
        counter_text = f"Selecionados: {selected_count}/{total_count}"
        
        # Título e contador alinhados
        title_padding = 79 - len("─ SETUP LIVCHAT ") - len(counter_text) - 3
        header_line = f"╭─ SETUP LIVCHAT {'─' * title_padding} {counter_text} ─╮"
        
        lines.append(f"{self.CINZA}{header_line}{self.RESET}")
        lines.append(f"{self.CINZA}│{self.BEGE} ↑/↓ navegar · → marcar (●/○) · Enter duplo executar · Esc voltar{self.CINZA}              │{self.RESET}")
        lines.append(f"{self.CINZA}│                                                                               │{self.RESET}")
        
        # Mostrar 11 itens: 5 acima + atual + 5 abaixo
        visible_items = 11
        center_position = 5
        
        # Calcular índices dos itens visíveis
        start_index = max(0, self.selected_index - center_position)
        end_index = min(len(self.apps), start_index + visible_items)
        
        # Ajustar se estamos no final da lista
        if end_index == len(self.apps) and len(self.apps) >= visible_items:
            start_index = max(0, len(self.apps) - visible_items)
        
        display_items = self.apps[start_index:end_index]
        
        # Preencher com linhas vazias se necessário
        while len(display_items) < visible_items:
            display_items.append(None)
        
        # Construir linhas dos itens
        for i, app in enumerate(display_items):
            actual_index = start_index + i if app else -1
            
            if app is None:
                # Linha vazia
                lines.append(f"{self.CINZA}│                                                                              │{self.RESET}")
            else:
                # Símbolo de seleção
                symbol = "●" if app["id"] in self.selected_items else "○"
                
                if actual_index == self.selected_index:
                    # Item em foco - seta à esquerda + texto branco
                    if app["id"] in self.selected_items:
                        # Selecionado + em foco - verde
                        text = f"→ {symbol} [{app['id']:2d}] {app['name']}"
                        padding = 78 - len(text)
                        lines.append(f"{self.CINZA}│ {self.VERDE}{text}{' ' * padding}{self.CINZA}│{self.RESET}")
                    else:
                        # Só em foco - branco
                        text = f"→ {symbol} [{app['id']:2d}] {app['name']}"
                        padding = 78 - len(text)
                        lines.append(f"{self.CINZA}│ {self.BRANCO}{text}{' ' * padding}{self.CINZA}│{self.RESET}")
                else:
                    # Item normal
                    if app["id"] in self.selected_items:
                        # Selecionado mas sem foco - verde
                        text = f"  {symbol} [{app['id']:2d}] {app['name']}"
                        padding = 78 - len(text)
                        lines.append(f"{self.CINZA}│ {self.VERDE}{text}{' ' * padding}{self.CINZA}│{self.RESET}")
                    else:
                        # Normal - cinza escuro para texto
                        text = f"  {symbol} [{app['id']:2d}] {app['name']}"
                        padding = 78 - len(text)
                        lines.append(f"{self.CINZA}│ {self.CINZA}{text}{' ' * padding}│{self.RESET}")
        
        # Footer com bordas arredondadas
        lines.append(f"{self.CINZA}│                                                                               │{self.RESET}")
        lines.append(f"{self.CINZA}╰───────────────────────────────────────────────────────────────────────────────╯{self.RESET}")
        lines.append(f"{self.BEGE}Legenda: ○ = não selecionado · ● = selecionado{self.RESET}")
        
        # Imprimir tudo de uma vez
        for line in lines:
            print(line)
    
    def find_next_unselected(self, start_index):
        """Encontra o próximo item não selecionado"""
        for i in range(start_index + 1, len(self.apps)):
            if self.apps[i]["id"] not in self.selected_items:
                return i
        # Se não encontrar, volta do início
        for i in range(0, start_index):
            if self.apps[i]["id"] not in self.selected_items:
                return i
        return start_index  # Todos selecionados
    
    def handle_input(self):
        """Gerencia entrada do usuário"""
        key = self.get_key()
        
        # Resetar timer de Enter para outras teclas
        current_time = time.time()
        if key != 'ENTER':
            self.last_enter_time = 0
            
        # Navegação com wraparound
        if key == 'UP' or key == 'k':
            if self.selected_index == 0:
                # Se está no primeiro, vai para o último (35)
                self.selected_index = len(self.apps) - 1
            else:
                self.selected_index -= 1
            return True
        elif key == 'DOWN' or key == 'j':
            if self.selected_index == len(self.apps) - 1:
                # Se está no último (35), volta para o primeiro (1)
                self.selected_index = 0
            else:
                self.selected_index += 1
            return True
            
        # Seleção
        elif key == ' ' or key == 'RIGHT':  # ESPAÇO ou seta direita
            current_app_id = self.apps[self.selected_index]["id"]
            if current_app_id in self.selected_items:
                self.selected_items.remove(current_app_id)
            else:
                self.selected_items.add(current_app_id)
            return True
            
        # Ctrl+A - Selecionar/desselecionar tudo
        elif key == 'CTRL_A':
            if len(self.selected_items) == len(self.apps):
                # Desselecionar tudo
                self.selected_items.clear()
            else:
                # Selecionar tudo
                self.selected_items = set(app["id"] for app in self.apps)
            return True
            
        # Tab - Próximo não selecionado
        elif key == 'TAB':
            next_index = self.find_next_unselected(self.selected_index)
            if next_index != self.selected_index:
                self.selected_index = next_index
                return True
            
        # Enter - Selecionar item atual
        elif key == 'ENTER':
            time_since_last = current_time - self.last_enter_time
            
            if self.last_enter_time > 0 and time_since_last <= self.double_click_threshold:
                # Enter duplo detectado (dentro do limite de tempo)
                self.last_enter_time = 0  # Reset
                return 'CONFIRM'
            else:
                # Enter simples - apenas selecionar/deselecionar
                current_app_id = self.apps[self.selected_index]["id"]
                if current_app_id in self.selected_items:
                    self.selected_items.remove(current_app_id)
                else:
                    self.selected_items.add(current_app_id)
                
                self.last_enter_time = current_time  # Marcar tempo do primeiro Enter
                return True
            
        # Sair
        elif key == 'ESC' or key == 'q' or key == 'Q':
            return 'EXIT'
        
        return False
    
    def run(self):
        """Loop principal do menu"""
        print(f"\n{self.VERDE}Bem-vindo ao Setup LivChat - Seleção Múltipla!{self.RESET}")
        
        try:
            self.setup_terminal()
            
            # Desenhar menu inicial
            self.draw_menu(first_draw=True)
            
            while True:
                action = self.handle_input()
                
                if action == 'EXIT':
                    print(f"\n{self.BEGE}Saindo...{self.RESET}")
                    return None
                elif action == 'CONFIRM':
                    return list(self.selected_items)
                elif action:  # True = redesenhar
                    # Calcular quantas linhas limpar (menu tem 17 linhas fixas)
                    lines_to_clear = 17
                    
                    # Limpar o menu anterior e redesenhar
                    for _ in range(lines_to_clear):
                        print("\x1b[1A\x1b[2K", end="")  # Sobe 1 linha e limpa a linha
                    self.draw_menu()
                    
        finally:
            self.restore_terminal()

def main():
    """Função principal do demo"""
    menu = SimpleTUIMenu()
    selected = menu.run()
    
    if selected:
        print(f"\n{menu.VERDE}ITENS SELECIONADOS:{menu.RESET}")
        for app_id in sorted(selected):
            app_name = next(app["name"] for app in menu.apps if app["id"] == app_id)
            print(f"{menu.AMARELO}  [{app_id}]{menu.BRANCO} {app_name}{menu.RESET}")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\033[91mSaindo...\033[0m")
        sys.exit(0)