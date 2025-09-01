#!/usr/bin/env python3
"""
Menu TUI Interativo com Status - Demonstração
Versão completa interativa com dados fake
"""

import sys
import termios
import tty
import time
import random
import threading

class InteractiveMenuDemo:
    """Menu TUI com seleção múltipla e status dos serviços"""
    
    # Cores do Setup (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    AZUL = "\033[34m"           # Blue - Para compatibility (legacy)
    AMARELO = "\033[93m"        # Yellow - Para warning states
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self):
        # Estado do menu TUI
        self.selected_index = 0
        self.selected_items = set()
        self.search_term = ""
        
        # Spinner animation
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0
        self.animation_running = False
        self.animation_thread = None
        
        # Lista de aplicações com status fake
        self.apps = self._generate_apps_with_status()
        
        # Cache para valores de CPU/MEM (atualização mais lenta)
        self.cpu_mem_cache = {}
        self.last_cpu_mem_update = 0
        
        # Para controle de terminal não-bloqueante
        self.old_settings = None
        
        # Para controle de linhas do menu anterior
        self.last_drawn_lines = 20
        
        # Largura ajustada: conteúdo termina em ~80, +12 espaços = 92 total
        self.menu_width = 92
    
    def _generate_apps_with_status(self):
        """Gera lista de apps com status fake"""
        base_apps = [
            {"id": "basic", "name": "Basic Setup (E-mail, Hostname, DNS)", "category": "infra"},
            {"id": "smtp", "name": "SMTP Setup (Configuração de Email)", "category": "infra"},
            {"id": "docker", "name": "Docker Swarm (Instalação e Config)", "category": "infra"},
            {"id": "traefik", "name": "Traefik (Proxy Reverso com SSL)", "category": "infra"},
            {"id": "portainer", "name": "Portainer (Gerenciador Docker)", "category": "infra"},
            {"id": "redis", "name": "Redis (Cache e Session Store)", "category": "database"},
            {"id": "postgres", "name": "PostgreSQL (Banco Relacional)", "category": "database"},
            {"id": "pgvector", "name": "PgVector (Extensão Vetorial)", "category": "database"},
            {"id": "minio", "name": "MinIO (S3 Compatible)", "category": "storage"},
            {"id": "chatwoot", "name": "Chatwoot (Plataforma de Suporte)", "category": "app"},
            {"id": "directus", "name": "Directus (Headless CMS)", "category": "app"},
            {"id": "n8n", "name": "N8N (Automação de Workflows)", "category": "app"},
            {"id": "grafana", "name": "Grafana (Monitoramento)", "category": "app"},
            {"id": "gowa", "name": "GOWA (WhatsApp API)", "category": "app"},
            {"id": "passbolt", "name": "Passbolt (Gerenciador Senhas)", "category": "app"},
            {"id": "evolution", "name": "Evolution API (WhatsApp v2)", "category": "app"},
            {"id": "cleanup", "name": "Cleanup (Limpeza do Ambiente)", "category": "util"},
        ]
        
        # Adicionar status fake para alguns serviços
        status_configs = {
            "basic": {"status": "configured", "replicas": None, "cpu": None, "mem": None},
            "smtp": {"status": "configured", "replicas": None, "cpu": None, "mem": None},
            "docker": {"status": "configured", "replicas": None, "cpu": None, "mem": None},
            "traefik": {"status": "running", "replicas": "1/1", "cpu": 2.5, "mem": 181},
            "portainer": {"status": "running", "replicas": "1/1", "cpu": 8.1, "mem": 192},
            "redis": {"status": "running", "replicas": "1/1", "cpu": 4.1, "mem": 137},
            "postgres": {"status": "running", "replicas": "1/1", "cpu": 2.4, "mem": 137},
            "pgvector": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "minio": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "chatwoot": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "directus": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "n8n": {"status": "running", "replicas": "2/2", "cpu": 12.3, "mem": 245},
            "grafana": {"status": "stopped", "replicas": "0/1", "cpu": None, "mem": None},
            "gowa": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "passbolt": {"status": None, "replicas": None, "cpu": None, "mem": None},
            "evolution": {"status": "updating", "replicas": "1/1", "cpu": 10.2, "mem": 189},
            "cleanup": {"status": None, "replicas": None, "cpu": None, "mem": None},
        }
        
        # Merge status com apps
        for app in base_apps:
            if app["id"] in status_configs:
                app.update(status_configs[app["id"]])
            else:
                app.update({"status": None, "replicas": None, "cpu": None, "mem": None})
        
        # Adicionar apps "Em breve" para completar 34 items
        for i in range(len(base_apps) + 1, 35):
            base_apps.append({
                "id": f"em_breve_{i}",
                "name": "Em breve",
                "category": "future",
                "status": None,
                "replicas": None,
                "cpu": None,
                "mem": None
            })
        
        return base_apps
    
    def get_filtered_apps(self):
        """Retorna lista filtrada de apps baseada no termo de pesquisa"""
        if not self.search_term:
            return self.apps
            
        filtered_apps = []
        search_lower = self.search_term.lower()
        
        # Busca por número exato
        if search_lower.isdigit():
            search_number = int(search_lower)
            if 1 <= search_number <= len(self.apps):
                target_app = self.apps[search_number - 1]
                filtered_apps.append(target_app)
                return filtered_apps
        
        # Busca por nome
        for app in self.apps:
            if app["name"].lower().startswith(search_lower):
                filtered_apps.append(app)
        
        for app in self.apps:
            if search_lower in app["name"].lower() and app not in filtered_apps:
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
                    if key3 == 'A':
                        return 'UP'
                    elif key3 == 'B':
                        return 'DOWN'
                    elif key3 == 'C':
                        return 'RIGHT'
                    elif key3 == 'D':
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
        elif ord(key) == 10 or ord(key) == 13:  # Enter
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
        
        # Título e contador alinhados (largura aumentada para 105)
        title_padding = self.menu_width - len("─ SETUP LIVCHAT ") - len(counter_text) - 5
        header_line = f"╭─ SETUP LIVCHAT {'─' * title_padding} {counter_text} ─╮"
        
        lines.append(f"{self.CINZA}{header_line}{self.RESET}")
        
        # Linha de instruções
        instrucoes = " ↑/↓ navegar · → marcar (●/○) · Enter executar · Digite para pesquisar"
        instrucoes_padding = self.menu_width - len(instrucoes) - 2
        lines.append(f"{self.CINZA}│{self.BEGE}{instrucoes}{' ' * instrucoes_padding}{self.CINZA}│{self.RESET}")
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        
        # Cabeçalho da tabela com alinhamento correto
        # APLICAÇÃO ocupa 60 chars, STATUS 8 chars, CPU 8 chars, MEM 5 chars
        header_text = " APLICAÇÃO" + " " * 50 + "STATUS    CPU     MEM"
        header_padding = self.menu_width - len(header_text) - 2
        lines.append(f"{self.CINZA}│{self.BRANCO}{header_text}{' ' * header_padding}{self.CINZA}│{self.RESET}")
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        
        # Filtrar apps baseado na pesquisa
        if self.search_term:
            current_apps = self.get_filtered_apps()
            
            if current_apps and self.selected_index >= len(current_apps):
                self.selected_index = 0
                
            # Mostrar linha de busca
            search_display = f"🔍 Filtro: {self.search_term}"
            result_count = len(current_apps)
            status = f" ({result_count}/{len(self.apps)} resultados)"
            search_text = search_display + status
            
            visual_length = len(search_text) + 1
            search_padding = self.menu_width - visual_length - 3
            lines.append(f"{self.CINZA}│ {self.BRANCO}{search_text}{' ' * search_padding}{self.CINZA}│{self.RESET}")
            lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        else:
            current_apps = self.apps
        
        # Mostrar até 11 itens
        visible_items = min(11, len(current_apps))
        center_position = min(5, visible_items // 2)
        
        # Calcular índices dos itens visíveis com rolagem
        if len(current_apps) <= visible_items:
            display_items = current_apps
        else:
            start_index = max(0, self.selected_index - center_position)
            end_index = min(len(current_apps), start_index + visible_items)
            
            if end_index == len(current_apps):
                start_index = max(0, len(current_apps) - visible_items)
                
            display_items = current_apps[start_index:end_index]
        
        # Preencher com linhas vazias se necessário
        while len(display_items) < visible_items:
            display_items.append(None)
        
        # Atualizar valores de CPU/MEM (menos frequente)
        current_time = time.time()
        if current_time - self.last_cpu_mem_update > 2.0:  # Atualiza a cada 2 segundos
            self.last_cpu_mem_update = current_time
            self._update_cpu_mem_values()
        
        # Construir linhas dos itens
        for i, app in enumerate(display_items):
            if app:
                actual_index = next((idx for idx, a in enumerate(self.apps) if a["id"] == app["id"]), -1)
                display_index = next((idx for idx, a in enumerate(current_apps) if a["id"] == app["id"]), -1)
            else:
                actual_index = -1
                display_index = -1
            
            if app is None:
                lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
            else:
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
                if app["status"] == "configured":
                    status_icon = f" {self.VERDE}✓{self.RESET}"
                elif app["status"] == "running":
                    spinner = self.spinner_chars[self.spinner_index]
                    status_icon = f" {self.VERDE}{spinner}{self.RESET}"
                elif app["status"] == "stopped":
                    status_icon = f" {self.VERMELHO}✗{self.RESET}"
                elif app["status"] == "updating":
                    spinner = self.spinner_chars[(self.spinner_index * 2) % len(self.spinner_chars)]
                    status_icon = f" {self.AMARELO}{spinner}{self.RESET}"
                else:
                    status_icon = ""
                
                # Montar parte da aplicação (60 chars total)
                name_with_icon = name + status_icon
                
                # Calcular padding para alinhar com as colunas
                # Precisamos considerar apenas os caracteres visíveis
                import re
                clean_name = re.sub(r'\033\[[0-9;]*m', '', name)
                if status_icon:
                    clean_name += " ✓"  # Adiciona 2 chars para o ícone
                
                # Total de espaço para aplicação: 60 chars (do cursor até STATUS)
                app_section_length = len(f"{cursor}{symbol} {item_number} {clean_name}")
                padding_to_status = 60 - app_section_length
                
                # Formatação das métricas
                status_str, cpu_str, mem_str = self._format_metrics(app, is_current)
                
                # Montar linha completa
                if is_current:
                    # Item com cursor - nome em branco
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
        
        # Legenda simplificada (corrigido alinhamento)
        if not self.search_term:
            legenda = "○/● = não selecionado/selecionado"
            legenda_padding = self.menu_width - len(legenda) - 3  # -3 para contar o espaço antes da legenda
            lines.append(f"{self.CINZA}│ {self.BEGE}{legenda}{' ' * legenda_padding}{self.CINZA}│{self.RESET}")
        
        # Footer
        lines.append(f"{self.CINZA}│{' ' * (self.menu_width - 2)}│{self.RESET}")
        footer_line = "─" * (self.menu_width - 2)
        lines.append(f"{self.CINZA}╰{footer_line}╯{self.RESET}")
        
        # Imprimir tudo de uma vez
        for line in lines:
            print(line)
            
        self.last_drawn_lines = len(lines)
    
    def _format_metrics(self, app, is_current):
        """Formata as métricas com cores apropriadas e alinhamento correto"""
        # Cor base para métricas
        if is_current:
            metric_color = self.BRANCO
        else:
            # Se o item está selecionado, métricas também ficam verdes
            if app["id"] in self.selected_items:
                metric_color = self.VERDE
            else:
                metric_color = self.CINZA
        
        # STATUS (réplicas) - ajustado para alinhar 2 espaços à esquerda
        if app["replicas"]:
            status_str = f"{metric_color}{app['replicas']:>5}{self.RESET}   "
        else:
            status_str = f"{metric_color}      {self.RESET}  "
        
        # CPU - 8 chars de largura
        if app["id"] in self.cpu_mem_cache and "cpu" in self.cpu_mem_cache[app["id"]]:
            cpu_val = self.cpu_mem_cache[app["id"]]["cpu"]
            cpu_str = f"{metric_color}{cpu_val:>5.1f}%{self.RESET}  "
        else:
            cpu_str = f"{metric_color}        {self.RESET}"
        
        # MEM - 5 chars de largura (movido 1 espaço para direita)
        if app["id"] in self.cpu_mem_cache and "mem" in self.cpu_mem_cache[app["id"]]:
            mem_val = self.cpu_mem_cache[app["id"]]["mem"]
            mem_str = f"{metric_color}{mem_val:>5.0f}M{self.RESET}"
        else:
            mem_str = f"{metric_color}      {self.RESET}"
        
        return status_str, cpu_str, mem_str
    
    def _update_cpu_mem_values(self):
        """Atualiza valores de CPU e memória com pequena variação"""
        for app in self.apps:
            if app["status"] == "running" or app["status"] == "updating":
                if app["cpu"] is not None:
                    # Pequena variação no CPU
                    base_cpu = app["cpu"]
                    variation = random.uniform(-0.3, 0.3)
                    new_cpu = max(0.1, min(99.9, base_cpu + variation))
                    
                    if app["id"] not in self.cpu_mem_cache:
                        self.cpu_mem_cache[app["id"]] = {}
                    self.cpu_mem_cache[app["id"]]["cpu"] = new_cpu
                
                if app["mem"] is not None:
                    # Pequena variação na memória
                    base_mem = app["mem"]
                    variation = random.uniform(-5, 5)
                    new_mem = max(10, min(999, base_mem + variation))
                    
                    if app["id"] not in self.cpu_mem_cache:
                        self.cpu_mem_cache[app["id"]] = {}
                    self.cpu_mem_cache[app["id"]]["mem"] = new_mem
    
    def animate_spinners(self):
        """Thread para animar os spinners"""
        while self.animation_running:
            time.sleep(0.1)  # Atualiza a cada 100ms (velocidade original)
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            
            # Limpar e redesenhar
            for _ in range(self.last_drawn_lines):
                print(f"\033[1A\033[2K", end="")
            self.draw_menu()
    
    def handle_input(self):
        """Gerencia entrada do usuário"""
        key = self.get_key()
        
        current_apps = self.get_filtered_apps() if self.search_term else self.apps
        
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
        elif key == ' ' or key == 'RIGHT':
            if self.selected_index < len(current_apps):
                current_app = current_apps[self.selected_index]
                if current_app["category"] != "future":
                    if current_app["id"] in self.selected_items:
                        self.selected_items.remove(current_app["id"])
                    else:
                        self.selected_items.add(current_app["id"])
            return True
        elif key == 'CTRL_A':
            if len(self.selected_items) == len([a for a in self.apps if a["category"] != "future"]):
                self.selected_items.clear()
            else:
                self.selected_items = set(app["id"] for app in self.apps if app["category"] != "future")
            return True
        elif key == 'ENTER':
            if self.selected_items:
                return 'CONFIRM'
            if self.selected_index < len(current_apps):
                current_app = current_apps[self.selected_index]
                if current_app["category"] != "future":
                    self.selected_items.add(current_app["id"])
                    if self.search_term:
                        self.search_term = ""
                        self.selected_index = 0
                    return 'CONFIRM'
            return True
        elif key == '\x7f' or key == '\b':  # Backspace
            if self.search_term:
                self.search_term = self.search_term[:-1]
                self.selected_index = 0
                return True
        elif key == 'ESC' or key == 'q' or key == 'Q':
            if self.search_term:
                self.search_term = ""
                return True
            else:
                return 'EXIT'
        elif len(key) == 1 and (key.isalnum() or key in ' -_.'):
            self.search_term += key.lower()
            self.selected_index = 0
            return True
        
        return False
    
    def run(self):
        """Executa o menu interativo com animação"""
        print(f"\n{self.VERDE}Demonstração do Menu com Status - Dados Simulados{self.RESET}")
        
        try:
            self.setup_terminal()
            
            # Iniciar thread de animação
            self.animation_running = True
            self.animation_thread = threading.Thread(target=self.animate_spinners, daemon=True)
            self.animation_thread.start()
            
            # Desenhar menu inicial
            self.draw_menu(first_draw=True)
            
            while True:
                action = self.handle_input()
                
                if action == 'EXIT':
                    self.animation_running = False
                    print(f"\n{self.BEGE}Saindo da demonstração...{self.RESET}")
                    return None
                elif action == 'CONFIRM':
                    self.animation_running = False
                    selected_apps = [app for app in self.apps if app["id"] in self.selected_items]
                    print(f"\n{self.VERDE}Apps selecionados para instalação:{self.RESET}")
                    for app in selected_apps:
                        idx = self.apps.index(app) + 1
                        print(f"  {self.BEGE}[{idx:2d}] {app['name']}{self.RESET}")
                    return list(self.selected_items)
                elif action:
                    # Redesenhar menu
                    for _ in range(self.last_drawn_lines):
                        print(f"\033[1A\033[2K", end="")
                    self.draw_menu()
                    
        finally:
            self.animation_running = False
            if self.animation_thread:
                self.animation_thread.join(timeout=0.5)
            self.restore_terminal()

def demo_static():
    """Demonstração estática do menu (sem interação)"""
    menu = InteractiveMenuDemo()
    
    # Simular algumas seleções
    menu.selected_items = {"traefik", "portainer", "redis", "postgres"}
    menu.selected_index = 6  # PostgreSQL
    
    print(f"\n{menu.VERDE}Demonstração do Menu com Status - Layout Estático{menu.RESET}")
    print(f"{menu.BEGE}Visualização do novo design com colunas STATUS, CPU e MEM:{menu.RESET}\n")
    
    # Desenhar menu sem interação
    menu.draw_menu(first_draw=True)
    
    print(f"\n{menu.BEGE}Recursos demonstrados:{menu.RESET}")
    print(f"  • Status inline: ✓ (configurado), ⠋ (rodando), ✗ (parado)")
    print(f"  • Cursor: > para indicar item atual")
    print(f"  • Cores: apenas símbolo ● fica verde quando selecionado")
    print(f"  • Métricas alinhadas com cabeçalho")
    print(f"  • Spinner rápido (100ms)")
    
    print(f"\n{menu.VERDE}Para executar o menu interativo real, use: sudo python3 main.py{menu.RESET}")

if __name__ == "__main__":
    import os
    
    # Verificar se estamos em ambiente interativo
    if os.isatty(sys.stdin.fileno()):
        try:
            menu = InteractiveMenuDemo()
            result = menu.run()
            
            if result:
                print(f"\n{menu.VERDE}Demonstração concluída!{menu.RESET}")
                print(f"{menu.BEGE}Este menu mostra como ficará com status real dos serviços.{menu.RESET}")
        except KeyboardInterrupt:
            print(f"\n\033[91mDemonstração interrompida.\033[0m")
            sys.exit(0)
        except termios.error:
            # Fallback para demonstração estática
            demo_static()
    else:
        # Modo não-interativo
        demo_static()