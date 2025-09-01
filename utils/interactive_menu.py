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
import threading
from typing import List, Dict
from utils.module_coordinator import ModuleCoordinator
from utils.docker_monitor import DockerMonitor

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
    AMARELO = "\033[93m"        # Yellow - Para warning/updating states
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.coordinator = ModuleCoordinator(args)
        
        # Estado do menu TUI
        self.selected_index = 0
        self.selected_items = set()
        self.search_term = ""  # Para funcionalidade de pesquisa
        
        # Monitor Docker para status real
        self.docker_monitor = None
        self.monitor_enabled = False
        self.services_status = {}  # Cache de status dos serviços
        
        # Spinner animation
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0
        self.animation_thread = None
        self.animation_running = False
        
        # Lista de aplicações disponíveis (34 itens)
        self.apps = [
            {"id": "basic", "name": "Basic Setup (E-mail, Hostname, Cloudflare, Rede, Timezone)", "category": "infra"},
            {"id": "smtp", "name": "SMTP Setup (Configuração de Email)", "category": "infra"},
            {"id": "docker", "name": "Docker Swarm (Instalação e Configuração)", "category": "infra"},
            {"id": "traefik", "name": "Traefik (Proxy Reverso com SSL)", "category": "infra"},
            {"id": "portainer", "name": "Portainer (Gerenciador Docker)", "category": "infra"},
            {"id": "redis", "name": "Redis (Cache e Session Store)", "category": "database"},
            {"id": "postgres", "name": "PostgreSQL (Banco de Dados Relacional)", "category": "database"},
            {"id": "pgvector", "name": "PgVector (Extensão Vetorial PostgreSQL)", "category": "database"},
            {"id": "minio", "name": "MinIO (Armazenamento S3 Compatible)", "category": "storage"},
            {"id": "chatwoot", "name": "Chatwoot (Plataforma de Suporte)", "category": "app"},
            {"id": "directus", "name": "Directus (Headless CMS)", "category": "app"},
            {"id": "n8n", "name": "N8N (Automação de Workflows)", "category": "app"},
            {"id": "grafana", "name": "Grafana (Monitoramento e Métricas)", "category": "app"},
            {"id": "gowa", "name": "GOWA (WhatsApp API Multi Device)", "category": "app"},
            {"id": "passbolt", "name": "Passbolt (Gerenciador de Senhas)", "category": "app"},
            {"id": "evolution", "name": "Evolution API (WhatsApp API v2)", "category": "app"},
            {"id": "cleanup", "name": "Cleanup (Limpeza Completa do Ambiente)", "category": "util"},
            {"id": "em_breve_18", "name": "Em breve", "category": "future"},
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
            {"id": "em_breve_34", "name": "Em breve", "category": "future"}
        ]
        
        # Para controle de terminal não-bloqueante
        self.old_settings = None
        
        # Para controle de enter (removido duplo clique)
        # self.last_enter_time = 0
        # self.double_click_threshold = 0.5  # 500ms
        
        # Para controle de linhas do menu anterior (evita sobreposição)
        self.last_drawn_lines = 20  # Valor inicial aumentado para novo layout
        
        # Largura do menu ajustada
        self.menu_width = 92
        
        # Inicializar monitor Docker se disponível
        self._init_docker_monitor()
    
    def _init_docker_monitor(self):
        """Inicializa o monitor Docker se disponível"""
        try:
            self.docker_monitor = DockerMonitor(update_interval=2.0)
            if self.docker_monitor.is_docker_available():
                self.docker_monitor.start_monitoring()
                self.monitor_enabled = True
                self.logger.debug("Monitor Docker iniciado com sucesso")
                # Aguardar coleta inicial
                time.sleep(2)
                # Obter dados iniciais
                self.services_status = self.docker_monitor.get_all_services()
            else:
                self.logger.debug("Docker não disponível, monitoramento desabilitado")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar monitor Docker: {e}")
            self.monitor_enabled = False
    
    def _start_animation(self):
        """Inicia thread de animação do spinner"""
        if not self.animation_running:
            self.animation_running = True
            self.animation_thread = threading.Thread(target=self._animate_spinner, daemon=True)
            self.animation_thread.start()
    
    def _stop_animation(self):
        """Para thread de animação"""
        self.animation_running = False
        if self.animation_thread:
            self.animation_thread.join(timeout=0.5)
    
    def _animate_spinner(self):
        """Thread para animar os spinners"""
        while self.animation_running:
            time.sleep(0.1)  # Atualiza a cada 100ms
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            
            # Atualizar status dos serviços (menos frequente)
            if self.spinner_index % 20 == 0:  # A cada 2 segundos
                if self.monitor_enabled and self.docker_monitor:
                    self.services_status = self.docker_monitor.get_all_services()
            
            # Forçar redesenho do menu para animar spinners
            self._redraw_menu()
    
    def _redraw_menu(self):
        """Redesenha o menu sem limpar input"""
        # Limpar linhas anteriores
        for _ in range(self.last_drawn_lines):
            print(f"\033[1A\033[2K", end="")
        # Desenhar novo menu
        self.draw_menu()
    
    def _get_service_status(self, app_id: str) -> dict:
        """Obtém status de um serviço específico"""
        # Para aplicações de infraestrutura que não são serviços Docker
        if app_id in ['basic', 'smtp', 'docker', 'cleanup']:
            # Verificar se foi configurado (poderia ler de ConfigManager)
            return {'status': 'configured', 'replicas': None, 'cpu': None, 'mem': None}
        
        # Primeiro tentar obter do cache atualizado
        if self.monitor_enabled and self.services_status:
            if app_id in self.services_status:
                return self.services_status[app_id]
        
        # Se não está no cache mas o monitor está habilitado, tentar obter diretamente
        if self.monitor_enabled and self.docker_monitor:
            return self.docker_monitor.get_service_status(app_id)
        
        # Serviço não instalado
        return {'status': None, 'replicas': None, 'cpu': None, 'mem': None}
    
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
        """Desenha o menu TUI com status dos serviços"""
        lines = []
        
        if first_draw:
            lines.append("")  # linha vazia inicial
        
        # Header com contador
        selected_count = len(self.selected_items)
        total_count = len(self.apps)
        counter_text = f"Selecionados: {selected_count}/{total_count}"
        
        # Título e contador alinhados
        title_padding = self.menu_width - len("─ SETUP LIVCHAT ") - len(counter_text) - 5
        header_line = f"╭─ SETUP LIVCHAT {'─' * title_padding} {counter_text} ─╮"
        
        lines.append(f"{self.CINZA}{header_line}{self.RESET}")
        
        # Linha de instruções
        instrucoes = " ↑/↓ navegar · → marcar (●/○) · Enter executar · Digite para pesquisar"
        instrucoes_padding = self.menu_width - len(instrucoes) - 2
        lines.append(f"{self.CINZA}│{self.BEGE}{instrucoes}{' ' * instrucoes_padding}{self.CINZA}│{self.RESET}")
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        
        # Cabeçalho da tabela
        header_text = " APLICAÇÃO" + " " * 50 + "STATUS    CPU     MEM"
        header_padding = self.menu_width - len(header_text) - 2
        lines.append(f"{self.CINZA}│{self.BRANCO}{header_text}{' ' * header_padding}{self.CINZA}│{self.RESET}")
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        
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
            search_padding = self.menu_width - visual_length - 3  # -3 para alinhar corretamente
            lines.append(f"{self.CINZA}│ {self.BRANCO}{search_text}{' ' * search_padding}{self.CINZA}│{self.RESET}")
            lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        else:
            current_apps = self.apps
        
        # Mostrar até 11 itens (ajustado para novo layout)
        visible_items = min(11, len(current_apps))
        center_position = min(5, visible_items // 2)
        
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
                lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
            else:
                # Obter status real do serviço
                service_status = self._get_service_status(app["id"])
                
                # É o item com cursor?
                is_current = display_index == self.selected_index
                
                # Símbolo de seleção
                is_selected = app["id"] in self.selected_items
                
                # Desabilita seleção para "Em breve"
                is_disabled = app["category"] == "future"
                if is_disabled:
                    is_selected = False
                
                # Formatação do item
                cursor = "> " if is_current else "  "
                symbol = "●" if is_selected else "○"
                
                # Cor do símbolo
                if is_selected:
                    symbol_color = self.VERDE
                else:
                    symbol_color = self.BRANCO if (is_current and not is_disabled) else self.CINZA
                
                # Número do item
                item_number = f"[{actual_index + 1:2d}]"
                
                # Nome com status inline
                name = app["name"]
                if len(name) > 40:
                    name = name[:37] + "..."
                
                # Status icon inline com o nome
                if service_status['status'] == 'configured':
                    status_icon = f" {self.VERDE}✓{self.RESET}"
                elif service_status['status'] == 'running':
                    spinner = self.spinner_chars[self.spinner_index]
                    status_icon = f" {self.VERDE}{spinner}{self.RESET}"
                elif service_status['status'] == 'stopped':
                    status_icon = f" {self.VERMELHO}✗{self.RESET}"
                elif service_status['status'] == 'updating':
                    spinner = self.spinner_chars[(self.spinner_index * 2) % len(self.spinner_chars)]
                    status_icon = f" {self.AMARELO}{spinner}{self.RESET}"
                else:
                    status_icon = ""
                
                # Calcular padding para alinhar com as colunas
                import re
                clean_name = re.sub(r'\033\[[0-9;]*m', '', name)
                if status_icon:
                    clean_name += " ✓"  # Adiciona 2 chars para o ícone
                
                # Total de espaço para aplicação: 60 chars
                app_section_length = len(f"{cursor}{symbol} {item_number} {clean_name}")
                padding_to_status = 60 - app_section_length
                
                # Formatação das métricas
                status_str, cpu_str, mem_str = self._format_metrics(service_status, is_current, is_selected)
                
                # Montar linha completa
                if is_current:
                    # Item com cursor
                    if is_selected:
                        # Cursor E selecionado - TUDO VERDE
                        line_content = f"{self.VERDE}{cursor}{symbol} {item_number} {name}{status_icon}{' ' * padding_to_status}{self.RESET}{status_str}{cpu_str}{mem_str}"
                    else:
                        # Cursor mas não selecionado - branco
                        line_content = f"{self.BRANCO}{cursor}{symbol_color}{symbol}{self.BRANCO} {item_number} {name}{status_icon}{' ' * padding_to_status}{self.RESET}{status_str}{cpu_str}{mem_str}"
                else:
                    # Item normal
                    if is_selected:
                        # TODA LINHA VERDE quando selecionada
                        line_content = f"{self.VERDE}{cursor}{symbol} {item_number} {name}{status_icon}{' ' * padding_to_status}{self.RESET}{status_str}{cpu_str}{mem_str}"
                    else:
                        # Tudo cinza
                        line_content = f"{self.CINZA}{cursor}{symbol} {item_number} {name}{status_icon}{' ' * padding_to_status}{self.RESET}{status_str}{cpu_str}{mem_str}"
                
                # Calcular padding final
                clean_line = re.sub(r'\033\[[0-9;]*m', '', line_content)
                final_padding = self.menu_width - len(clean_line) - 2
                
                lines.append(f"{self.CINZA}│{self.RESET}{line_content}{' ' * final_padding}{self.CINZA}│{self.RESET}")
        
        # Legenda simplificada
        if not self.search_term:
            legenda = "○/● = não selecionado/selecionado"
            legenda_padding = self.menu_width - len(legenda) - 3
            lines.append(f"{self.CINZA}│ {self.BEGE}{legenda}{' ' * legenda_padding}{self.CINZA}│{self.RESET}")
        
        # Footer
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        footer_line = "─" * (self.menu_width - 2)
        lines.append(f"{self.CINZA}╰{footer_line}╯{self.RESET}")
        
        # Imprimir tudo de uma vez
        for line in lines:
            print(line)
            
        # Atualiza contador de linhas desenhadas para próxima limpeza
        self.last_drawn_lines = len(lines)
    
    def _format_metrics(self, service_status: dict, is_current: bool, is_selected: bool):
        """Formata as métricas com cores apropriadas"""
        # Cor base para métricas
        if is_selected:
            metric_color = self.VERDE
        elif is_current:
            metric_color = self.BRANCO
        else:
            metric_color = self.CINZA
        
        # STATUS (réplicas) - ajustado para alinhar
        if service_status['replicas']:
            status_str = f"{metric_color}{service_status['replicas']:>5}{self.RESET}   "
        else:
            status_str = f"{metric_color}      {self.RESET}  "
        
        # CPU - 8 chars de largura
        if service_status['cpu'] is not None:
            cpu_str = f"{metric_color}{service_status['cpu']:>5.1f}%{self.RESET} "
        else:
            cpu_str = f"{metric_color}        {self.RESET}"
        
        # MEM - 5 chars de largura
        if service_status['mem'] is not None:
            mem_str = f"{metric_color}{service_status['mem']:>5.0f}M{self.RESET}"
        else:
            mem_str = f"{metric_color}      {self.RESET}"
        
        return status_str, cpu_str, mem_str
    
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
            
            # Iniciar animação se monitor estiver habilitado e houver serviços rodando
            if self.monitor_enabled:
                # Verificar se há algum serviço rodando
                has_running_services = any(
                    s.get('status') == 'running' 
                    for s in self.services_status.values()
                )
                if has_running_services:
                    self._start_animation()
            
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
                    # Se a animação NÃO está rodando, redesenhar manualmente
                    if not self.animation_running:
                        # Usa o contador de linhas do desenho anterior
                        lines_to_clear = self.last_drawn_lines
                        
                        # Sobe N linhas e limpa cada uma
                        for _ in range(lines_to_clear):
                            print(f"\033[1A\033[2K", end="")  # Sobe 1 linha e limpa
                        
                        self.draw_menu()
                    
        finally:
            # Parar animação
            if self.monitor_enabled:
                self._stop_animation()
            
            # Parar monitor Docker
            if self.docker_monitor:
                self.docker_monitor.stop_monitoring()
            
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
