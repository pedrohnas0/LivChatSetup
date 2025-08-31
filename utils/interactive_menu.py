#!/usr/bin/env python3
"""
Menu TUI Interativo v2.0 - LivChatSetup
Seleção múltipla com rolagem, baseado no demo_tui_simple.py
"""

import sys
import termios
import tty
import time
import logging
from typing import List, Dict
from utils.module_coordinator import ModuleCoordinator

class InteractiveMenu:
    """Menu TUI com seleção múltipla e rolagem"""
    
    # Cores do Setup (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    AZUL = "\033[34m"           # Blue - Para compatibility (legacy)
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.coordinator = ModuleCoordinator(args)
        
        # Estado do menu TUI
        self.selected_index = 0
        self.selected_items = set()
        self.search_term = ""  # Para funcionalidade de pesquisa
        
        # Lista de aplicações disponíveis (34 itens)
        self.apps = [
            {"id": "basic", "name": "Config (E-mail, Hostname, Cloudflare, Rede, Timezone)", "category": "infra"},
            {"id": "docker", "name": "Instalação do Docker + Swarm", "category": "infra"},
            {"id": "traefik", "name": "Instalação do Traefik (Proxy Reverso)", "category": "infra"},
            {"id": "portainer", "name": "Instalação do Portainer (Gerenciador Docker)", "category": "infra"},
            {"id": "redis", "name": "Redis (Cache/Session Store)", "category": "database"},
            {"id": "postgres", "name": "PostgreSQL (Banco Relacional)", "category": "database"},
            {"id": "pgvector", "name": "PostgreSQL + PgVector (Banco Vetorial)", "category": "database"},
            {"id": "minio", "name": "MinIO (S3 Compatible Storage)", "category": "storage"},
            {"id": "chatwoot", "name": "Chatwoot (Customer Support Platform)", "category": "app"},
            {"id": "directus", "name": "Directus (Headless CMS)", "category": "app"},
            {"id": "n8n", "name": "N8N (Workflow Automation)", "category": "app"},
            {"id": "grafana", "name": "Grafana (Stack de Monitoramento)", "category": "app"},
            {"id": "gowa", "name": "GOWA (WhatsApp API Multi Device)", "category": "app"},
            {"id": "livchatbridge", "name": "LivChatBridge (Webhook Connector)", "category": "app"},
            {"id": "passbolt", "name": "Passbolt (Password Manager)", "category": "app"},
            {"id": "cleanup", "name": "Limpeza Completa do Ambiente", "category": "util"},
            {"id": "evolution", "name": "Evolution API v2 (WhatsApp API)", "category": "app"},
            {"id": "em_breve_19", "name": "Em breve", "category": "future"},
            {"id": "em_breve_20", "name": "Em breve", "category": "future"},
            {"id": "em_breve_21", "name": "Em breve", "category": "future"},
            {"id": "em_breve_22", "name": "Em breve", "category": "future"},
            {"id": "em_breve_23", "name": "Em breve", "category": "future"},
            {"id": "em_breve_24", "name": "Em breve", "category": "future"},
            {"id": "em_breve_25", "name": "Em breve", "category": "future"},
            {"id": "em_breve_26", "name": "Em breve", "category": "future"},
            {"id": "em_breve_27", "name": "Em breve", "category": "future"},
            {"id": "em_breve_28", "name": "Em breve", "category": "future"},
            {"id": "em_breve_29", "name": "Em breve", "category": "future"},
            {"id": "em_breve_30", "name": "Em breve", "category": "future"},
            {"id": "em_breve_31", "name": "Em breve", "category": "future"},
            {"id": "em_breve_32", "name": "Em breve", "category": "future"},
            {"id": "em_breve_33", "name": "Em breve", "category": "future"},
            {"id": "em_breve_34", "name": "Em breve", "category": "future"},
            {"id": "em_breve_35", "name": "Em breve", "category": "future"}
        ]
        
        # Para controle de terminal não-bloqueante
        self.old_settings = None
        
        # Para controle de enter (removido duplo clique)
        # self.last_enter_time = 0
        # self.double_click_threshold = 0.5  # 500ms
        
        # Para controle de linhas do menu anterior (evita sobreposição)
        self.last_drawn_lines = 15  # Valor inicial
    
    def get_filtered_apps(self):
        """Retorna lista filtrada de apps baseada no termo de pesquisa (incluindo números)"""
        if not self.search_term:
            return self.apps
            
        filtered_apps = []
        search_lower = self.search_term.lower()
        
        # Primeira prioridade: busca por número exato (ex: "1", "2", "10")
        if search_lower.isdigit():
            search_number = int(search_lower)
            # Verifica se o número está dentro do range válido (1-34)
            if 1 <= search_number <= len(self.apps):
                target_app = self.apps[search_number - 1]  # Ajustar para índice 0
                filtered_apps.append(target_app)
                return filtered_apps
        
        # Segunda prioridade: nome que começa com o termo
        for app in self.apps:
            if app["name"].lower().startswith(search_lower):
                filtered_apps.append(app)
        
        # Terceira prioridade: nome que contém o termo (evitar duplicatas)
        for app in self.apps:
            if search_lower in app["name"].lower() and app not in filtered_apps:
                filtered_apps.append(app)
        
        # Quarta prioridade: ID que contém o termo (evitar duplicatas)
        for app in self.apps:
            if search_lower in app["id"].lower() and app not in filtered_apps:
                filtered_apps.append(app)
        
        # Quinta prioridade: busca por número no início do nome (ex: "[1]", "[10]")
        for i, app in enumerate(self.apps, 1):
            app_number = str(i)
            if search_lower in app_number and app not in filtered_apps:
                filtered_apps.append(app)
                
        return filtered_apps if filtered_apps else self.apps
        
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
                else:
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
        """Desenha o menu TUI com bordas arredondadas"""
        lines = []
        
        if first_draw:
            lines.append("")  # linha vazia inicial
        
        # Header com contador
        selected_count = len(self.selected_items)
        total_count = len(self.apps)
        counter_text = f"Selecionados: {selected_count}/{total_count}"
        
        # Título e contador alinhados (largura 101 caracteres internos)
        title_padding = 79 - len("─ SETUP LIVCHAT ") - len(counter_text) - 3
        header_line = f"╭─ SETUP LIVCHAT {'─' * title_padding} {counter_text} ─╮"
        
        lines.append(f"{self.CINZA}{header_line}{self.RESET}")
        # Linha de instruções com padding dinâmico
        instrucoes = " ↑/↓ navegar · → marcar (●/○) · Enter executar · Digite para pesquisar"
        instrucoes_padding = 79 - len(instrucoes)  # Texto já inclui espaço inicial
        lines.append(f"{self.CINZA}│{self.BEGE}{instrucoes}{' ' * instrucoes_padding}{self.CINZA}│{self.RESET}")
        lines.append(f"{self.CINZA}│                                                                               │{self.RESET}")
        
        # Filtrar apps baseado na pesquisa
        if self.search_term:
            current_apps = self.get_filtered_apps()
            
            # Ajustar selected_index para apps filtrados
            if current_apps and self.selected_index >= len(current_apps):
                self.selected_index = 0
                
            # Mostrar linha de busca logo após o header
            search_display = f"🔍 Filtro: {self.search_term}"
            result_count = len(current_apps)
            status = f" ({result_count}/{len(self.apps)} resultados)"
            search_text = search_display + status
            
            # Calcular padding considerando que emoji ocupa 2 caracteres visuais mas conta como 1 no len()
            # O emoji 🔍 conta como 1 no len() mas ocupa 2 espaços visuais
            visual_length = len(search_text) + 1  # +1 pelo emoji extra visual
            search_padding = 79 - visual_length - 1  # -1 pelo espaço inicial
            lines.append(f"{self.CINZA}│ {self.BRANCO}{search_text}{' ' * search_padding}{self.CINZA}│{self.RESET}")
            lines.append(f"{self.CINZA}│                                                                               │{self.RESET}")
        else:
            current_apps = self.apps
        
        # Mostrar até 9 itens filtrados (para dar espaço à caixa de pesquisa)
        visible_items = min(9, len(current_apps))
        center_position = min(4, visible_items // 2)
        
        # Calcular índices dos itens visíveis
        if len(current_apps) <= visible_items:
            display_items = current_apps
        else:
            start_index = max(0, self.selected_index - center_position)
            end_index = min(len(current_apps), start_index + visible_items)
            
            # Ajustar se estamos no final da lista
            if end_index == len(current_apps):
                start_index = max(0, len(current_apps) - visible_items)
                
            display_items = current_apps[start_index:end_index]
        
        # Preencher com linhas vazias se necessário
        while len(display_items) < visible_items:
            display_items.append(None)
        
        # Construir linhas dos itens
        for i, app in enumerate(display_items):
            # Encontrar o índice real no array original para numeração correta
            if app:
                actual_index = next((idx for idx, a in enumerate(self.apps) if a["id"] == app["id"]), -1)
                display_index = next((idx for idx, a in enumerate(current_apps) if a["id"] == app["id"]), -1)
            else:
                actual_index = -1
                display_index = -1
            
            if app is None:
                # Linha vazia
                lines.append(f"{self.CINZA}│                                                                              │{self.RESET}")
            else:
                # Símbolo de seleção
                symbol = "●" if app["id"] in self.selected_items else "○"
                
                # Número do item (baseado no índice + 1)
                item_number = f"[{actual_index + 1:2d}]"
                
                # Desabilita seleção para "Em breve"
                is_disabled = app["category"] == "future"
                if is_disabled:
                    symbol = "○"  # Sempre não selecionado
                
                if display_index == self.selected_index:
                    # Item atual com seta elegante (estilo original)
                    if app["id"] in self.selected_items and not is_disabled:
                        # Selecionado + atual - seta branca + verde
                        text_content = f"→ {symbol} {item_number} {app['name']}"
                        padding = 78 - len(text_content)
                        lines.append(f"{self.CINZA}│ {self.BRANCO}→ {self.VERDE}{symbol} {item_number} {app['name']}{' ' * padding}{self.CINZA}│{self.RESET}")
                    else:
                        # Só atual - seta branca (ou cinza se desabilitado)
                        text_content = f"→ {symbol} {item_number} {app['name']}"
                        padding = 78 - len(text_content)
                        if is_disabled:
                            lines.append(f"{self.CINZA}│ → {symbol} {item_number} {app['name']}{' ' * padding}│{self.RESET}")
                        else:
                            lines.append(f"{self.CINZA}│ {self.BRANCO}→ {symbol} {item_number} {app['name']}{' ' * padding}{self.CINZA}│{self.RESET}")
                else:
                    # Item normal - sem seta (2 espaços para alinhar com "→ ")
                    if app["id"] in self.selected_items and not is_disabled:
                        # Selecionado mas sem foco - verde simples
                        text_content = f"  {symbol} {item_number} {app['name']}"
                        padding = 78 - len(text_content)
                        lines.append(f"{self.CINZA}│ {self.VERDE}  {symbol} {item_number} {app['name']}{' ' * padding}{self.CINZA}│{self.RESET}")
                    else:
                        # Normal - cinza para texto
                        text_content = f"  {symbol} {item_number} {app['name']}"
                        padding = 78 - len(text_content)
                        lines.append(f"{self.CINZA}│   {symbol} {item_number} {app['name']}{' ' * padding}│{self.RESET}")
        
        # Footer com legenda (só quando não há busca)
        if not self.search_term:
            # Mostrar legenda quando não há pesquisa
            legenda = "Legenda: ○ = não selecionado · ● = selecionado"
            legenda_padding = 78 - len(legenda)
            lines.append(f"{self.CINZA}│ {self.BEGE}{legenda}{' ' * legenda_padding}{self.CINZA}│{self.RESET}")
        
        # Footer com bordas arredondadas
        lines.append(f"{self.CINZA}│                                                                               │{self.RESET}")
        lines.append(f"{self.CINZA}╰───────────────────────────────────────────────────────────────────────────────╯{self.RESET}")
        
        # Imprimir tudo de uma vez
        for line in lines:
            print(line)
            
        # Atualiza contador de linhas desenhadas para próxima limpeza
        self.last_drawn_lines = len(lines)
    
    def get_filtered_apps_by_term(self, term):
        """Filtra apps por termo de pesquisa"""
        filtered = []
        term_lower = term.lower()
        
        # Prioridade 1: Nome começa com termo
        for app in self.apps:
            if app["name"].lower().startswith(term_lower):
                filtered.append(app)
        
        # Prioridade 2: Nome contém termo (evitar duplicatas)
        for app in self.apps:
            if term_lower in app["name"].lower() and app not in filtered:
                filtered.append(app)
        
        # Prioridade 3: ID contém termo (evitar duplicatas)
        for app in self.apps:
            if term_lower in app["id"].lower() and app not in filtered:
                filtered.append(app)
        
        return filtered if filtered else self.apps

    
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
        
        # Removido controle de enter duplo
        # current_time = time.time()
        # if key != 'ENTER':
        #     self.last_enter_time = 0
            
        # Navegação considerando filtragem
        # Determinar lista atual (filtrada ou completa)
        if self.search_term:
            current_apps = self.get_filtered_apps()
        else:
            current_apps = self.apps
            
        if key == 'UP' or key == 'k':
            if self.selected_index == 0:
                self.selected_index = len(current_apps) - 1
            else:
                self.selected_index -= 1
            return True
        elif key == 'DOWN' or key == 'j':
            if self.selected_index == len(current_apps) - 1:
                self.selected_index = 0
            else:
                self.selected_index += 1
            return True
            
        # Seleção
        elif key == ' ' or key == 'RIGHT':  # ESPAÇO ou seta direita
            if self.selected_index < len(current_apps):
                current_app = current_apps[self.selected_index]
                current_app_id = current_app["id"]
            else:
                return True
            
            # Não permite seleção de itens "Em breve"
            if current_app["category"] == "future":
                return True
                
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
            
        # Enter - Executar se há itens selecionados, senão seleciona item atual e executa
        elif key == 'ENTER':
            # Se há itens selecionados, executa
            if self.selected_items:
                return 'CONFIRM'
            
            # Se não há itens selecionados, seleciona o item atual e executa imediatamente
            if self.selected_index < len(current_apps):
                current_app = current_apps[self.selected_index]
                current_app_id = current_app["id"]
                
                # Não permite seleção de itens "Em breve"
                if current_app["category"] != "future":
                    self.selected_items.add(current_app_id)
                    # Limpa pesquisa se houver
                    if self.search_term:
                        self.search_term = ""
                        self.selected_index = 0
                    # Executa imediatamente após selecionar
                    return 'CONFIRM'
            
            return True
                    
        # Backspace - Apagar último caractere da pesquisa
        elif key == '\x7f' or key == '\b':  # Backspace
            if self.search_term:
                self.search_term = self.search_term[:-1]
                # Reset para início quando limpa pesquisa
                self.selected_index = 0
                return True
            
        # Sair ou limpar pesquisa
        elif key == 'ESC' or key == 'q' or key == 'Q':
            if self.search_term:
                # Limpa pesquisa em vez de sair
                self.search_term = ""
                return True
            else:
                return 'EXIT'
        
        # Captura de caracteres para pesquisa
        elif len(key) == 1 and (key.isalnum() or key in ' -_.'):
            self.search_term += key.lower()
            # Reset para início ao começar nova pesquisa
            self.selected_index = 0
            return True
        
        return False
        
    def run_tui_menu(self):
        """Executa o menu TUI com seleção múltipla"""
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
                    # Usa o contador de linhas do desenho anterior
                    lines_to_clear = self.last_drawn_lines
                    
                    # Sobe N linhas e limpa cada uma
                    for _ in range(lines_to_clear):
                        print(f"\033[1A\033[2K", end="")  # Sobe 1 linha e limpa
                    
                    self.draw_menu()
                    
        finally:
            self.restore_terminal()
    
    def execute_selected_apps(self, selected_modules: List[str]) -> bool:
        """Executa as aplicações selecionadas"""
        if not selected_modules:
            print(f"\n{self.BEGE}Nenhuma aplicação selecionada.{self.RESET}")
            return True
            
        print(f"\n{self.VERDE}Executando {len(selected_modules)} aplicação(ões) selecionada(s)...{self.RESET}")
        
        # Usa o novo método de instalação múltipla do coordinator
        return self.coordinator.run_multiple_modules(selected_modules)
    
    def show_selection_summary(self, selected_modules: List[str]):
        """Exibe resumo dos itens selecionados"""
        if not selected_modules:
            return
            
        print(f"\n{self.VERDE}🎯 ITENS SELECIONADOS:{self.RESET}")
        for app_id in selected_modules:
            app = next((app for app in self.apps if app["id"] == app_id), None)
            if app:
                # Encontra o número do item
                item_number = next((i+1 for i, a in enumerate(self.apps) if a["id"] == app_id), 0)
                print(f"{self.BEGE}  [{item_number:2d}] {app['name']}{self.RESET}")
        print()
    
    def confirm_execution(self, selected_modules: List[str]) -> bool:
        """Exibe tela de confirmação para execução"""
        print(f"{self.VERDE}Confirmar execução de {len(selected_modules)} aplicação(ões)?{self.RESET}")
        print(f"{self.BEGE}Enter = Executar · Esc = Voltar ao menu{self.RESET}")
        
        try:
            self.setup_terminal()
            
            while True:
                key = self.get_key()
                
                if key == 'ENTER':
                    return True
                elif key == 'ESC':
                    return False
                    
        finally:
            self.restore_terminal()
    
    def show_ascii_art(self):
        """Exibe ASCII art do LivChat"""
        print(f"\n{self.BEGE}     ██╗     ██╗██╗   ██╗ ██████╗██╗  ██╗ █████╗ ████████╗{self.RESET}")
        print(f"{self.BEGE}     ██║     ██║██║   ██║██╔════╝██║  ██║██╔══██╗╚══██╔══╝{self.RESET}")
        print(f"{self.BEGE}     ██║     ██║██║   ██║██║     ███████║███████║   ██║   {self.RESET}")
        print(f"{self.BEGE}     ██║     ██║╚██╗ ██╔╝██║     ██╔══██║██╔══██║   ██║   {self.RESET}")
        print(f"{self.BEGE}     ███████╗██║ ╚████╔╝ ╚██████╗██║  ██║██║  ██║   ██║   {self.RESET}")
        print(f"{self.BEGE}     ╚══════╝╚═╝  ╚═══╝   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   {self.RESET}")
        print(f"\n{self.BEGE}                        Setup Modular v2.0{self.RESET}")
    
    def run(self):
        """Executa o menu interativo principal"""
        self.show_ascii_art()
        
        while True:
            # Executa o menu TUI
            selected_modules = self.run_tui_menu()
            
            if selected_modules is None:
                print(f"\n{self.VERDE}Obrigado por usar o Setup LivChat!{self.RESET}")
                return True
            
            # Exibe resumo e pede confirmação
            self.show_selection_summary(selected_modules)
            
            if self.confirm_execution(selected_modules):
                # Usuário confirmou - executar
                success = self.execute_selected_apps(selected_modules)
                
                if success:
                    print(f"\n{self.VERDE}✅ Instalação concluída com sucesso!{self.RESET}")
                else:
                    print(f"\n{self.VERMELHO}❌ Instalação concluída com falhas.{self.RESET}")
                
                # Perguntar se quer instalar algo mais seguindo padrão Enter/Ctrl+C
                try:
                    input(f"\n{self.BEGE}Pressione {self.VERDE}Enter{self.BEGE} para instalar mais aplicações ou {self.VERMELHO}Ctrl+C{self.BEGE} para encerrar...{self.RESET}")
                    
                    # Se chegou aqui, usuário pressionou Enter - voltar ao menu
                    print(f"\n{self.BEGE}Retornando ao menu principal...{self.RESET}")
                    # Limpa seleções para começar fresh
                    self.selected_items.clear()
                    self.selected_index = 0
                    # continua o loop do while True do menu principal
                    
                except KeyboardInterrupt:
                    print(f"\n{self.VERDE}Obrigado por usar o Setup LivChat!{self.RESET}")
                    return success
            else:
                # Usuário cancelou - volta ao menu
                print(f"\n{self.BEGE}Voltando ao menu de seleção...{self.RESET}")
                # Limpa seleções para começar fresh (opcional)
                # self.selected_items.clear()
                continue
