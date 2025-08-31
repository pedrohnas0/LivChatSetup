#!/usr/bin/env python3
"""
Coordenador de Módulos - Refatorado v2.0
Suporta seleção múltipla, dependências automáticas e configurações centralizadas
"""

import sys
import os
import termios
import tty
from datetime import datetime
from typing import List, Dict, Optional

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import setup_logging
from utils.config_manager import ConfigManager
from setup.basic_setup import BasicSetup
from setup.docker_setup import DockerSetup
from setup.traefik_setup import TraefikSetup
from setup.portainer_setup import PortainerSetup
from setup.cleanup_setup import CleanupSetup
from setup.redis_setup import RedisSetup
from setup.postgres_setup import PostgresSetup
from setup.pgvector_setup import PgVectorSetup
from setup.minio_setup import MinioSetup
from setup.chatwoot_setup import ChatwootSetup
from setup.n8n_setup import N8NSetup
from setup.grafana_setup import GrafanaSetup
from setup.gowa_setup import GowaSetup
from setup.livchatbridge_setup import LivChatBridgeSetup
from setup.directus_setup import DirectusSetup
from setup.passbolt_setup import PassboltSetup
from setup.evolution_setup import EvolutionSetup

class ModuleCoordinator:
    """Coordenador avançado dos módulos de setup - v2.0
    
    Suporta:
    - Seleção múltipla de aplicações
    - Resolução automática de dependências  
    - Configurações centralizadas em JSON
    - Gerenciamento DNS automático
    - Sugestões de senhas e configurações
    """
    
    # Cores para menus (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal de forma segura"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback
    
    def _print_box_title(self, title: str, width: int = None):
        """Cria box com título seguindo padrão do projeto - versão melhorada"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(80, terminal_width - 4)  # Margem de segurança
        
        # Remove códigos de cor para calcular tamanho real
        import re
        clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
        
        line = "─" * (width - 1)
        print(f"{self.CINZA}╭{line}╮{self.RESET}")
        
        # Centralização perfeita usando Python
        content_width = width - 2  # Descontar as bordas │ │
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor laranja ao título centralizado
        colored_title = f"{self.LARANJA}{clean_title}{self.RESET}"
        colored_line = centered_clean.replace(clean_title, colored_title)
            
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
        
    def _print_section_box(self, title: str, width: int = None):
        """Cria box de seção menor - versão melhorada"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(60, terminal_width - 10)  # Mais compacto
        
        # Remove códigos de cor para calcular tamanho real
        import re
        clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
        
        line = "─" * (width - 1)
        print(f"\n{self.CINZA}╭{line}╮{self.RESET}")
        
        # Centralização perfeita
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor bege ao título centralizado
        colored_title = f"{self.BEGE}{clean_title}{self.RESET}"
        colored_line = centered_clean.replace(clean_title, colored_title)
            
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def _clear_lines(self, count: int):
        """Limpa linhas específicas em vez de limpar toda a tela"""
        for _ in range(count):
            print("\033[F\033[K", end="")  # Move cursor up e limpa linha
    
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging()
        self.start_time = datetime.now()
        self.config = ConfigManager()
        
        # Carrega configurações do JSON centralizado
        self._load_persisted_configs()
        
        # Para controle de dependências automáticas
        self.dependency_modules = set()
        
        # Mapeamento de dependências
        self.dependencies = {
            'docker': ['basic'],
            'traefik': ['docker'],
            'portainer': ['traefik'],  # Portainer precisa do Traefik para SSL
            'redis': ['portainer'],     # Todos os serviços via API precisam do Portainer
            'postgres': ['portainer'],  # Todos os serviços via API precisam do Portainer
            'pgvector': ['portainer'],  # Todos os serviços via API precisam do Portainer
            'minio': ['portainer'],     # Todos os serviços via API precisam do Portainer
            'chatwoot': ['traefik', 'pgvector'],
            'directus': ['traefik', 'pgvector'], 
            'n8n': ['traefik', 'postgres'],
            'grafana': ['traefik'],
            'passbolt': ['traefik', 'postgres'],
            'evolution': ['traefik', 'postgres', 'redis'],
            'gowa': ['traefik'],
            'livchatbridge': ['traefik']
        }
        
        # Ordem de instalação (infraestrutura primeiro)
        self.install_order = [
            'basic', 'docker', 'traefik', 'portainer',
            'redis', 'postgres', 'pgvector', 'minio'
        ]
    
    def get_key(self):
        """Lê uma tecla do terminal (utilitário para menus scrollable)"""
        old_settings = termios.tcgetattr(sys.stdin.fileno())
        try:
            tty.setcbreak(sys.stdin.fileno())
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
                    return 'ESC'
                except:
                    return 'ESC'
            
            if ord(key) == 10 or ord(key) == 13:  # Enter
                return 'ENTER'
                
            return key
        finally:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
    
    def select_cloudflare_zone(self, zones: List[Dict]) -> Optional[Dict]:
        """Menu com pesquisa para seleção de zona Cloudflare"""
        if not zones:
            return None
            
        selected_index = 0
        search_term = ""
        last_lines_printed = 0
        first_run = True
        
        def get_filtered_zones():
            """Retorna zonas filtradas pelo termo de pesquisa"""
            if not search_term:
                return zones
                
            filtered = []
            search_lower = search_term.lower()
            
            # Primeira prioridade: nome que começa com o termo
            for zone in zones:
                if zone['name'].lower().startswith(search_lower):
                    filtered.append(zone)
            
            # Segunda prioridade: contém o termo
            for zone in zones:
                if search_lower in zone['name'].lower() and zone not in filtered:
                    filtered.append(zone)
                    
            return filtered
        
        while True:
            # Limpa apenas as linhas do menu anterior (não o cabeçalho)
            if not first_run and last_lines_printed > 0:
                self._clear_lines(last_lines_printed)
            first_run = False
            
            # Contar linhas que vamos imprimir
            lines_to_print = 0
            
            # Header com box (só na primeira vez)
            if last_lines_printed == 0:
                self._print_section_box("🌐 SELEÇÃO DE ZONA CLOUDFLARE")
                lines_to_print += 3  # Box tem 3 linhas
            
            print(f"{self.BEGE}↑/↓ navegar · Enter confirmar · Digite para pesquisar · Esc cancelar{self.RESET}")
            print("")
            lines_to_print += 2
            
            # Filtrar zonas baseado na pesquisa
            if search_term:
                current_zones = get_filtered_zones()
                
                # Ajustar selected_index para zonas filtradas
                if selected_index >= len(current_zones):
                    selected_index = max(0, len(current_zones) - 1)
                
                # Mostrar linha de busca
                search_display = f"🔍 Filtro: {search_term}"
                result_count = len(current_zones)
                status = f" ({result_count}/{len(zones)} resultados)"
                print(f"{self.VERDE}{search_display}{status}{self.RESET}")
                print("")
                lines_to_print += 2
            else:
                current_zones = zones
            
            # Lista zonas filtradas
            if not current_zones:
                print(f"{self.VERMELHO}Nenhuma zona encontrada com '{search_term}'{self.RESET}")
                lines_to_print += 1
            else:
                for i, zone in enumerate(current_zones):
                    status_icon = "✅" if zone.get('status') == 'active' else "⚠️"
                    zone_name = zone['name']
                    
                    if i == selected_index:
                        print(f"  {self.BRANCO}→ [{i + 1:2d}] {status_icon} {zone_name}{self.RESET}")
                    else:
                        print(f"    [{i + 1:2d}] {status_icon} {zone_name}")
                    lines_to_print += 1
                
                # Status da seleção
                if current_zones:
                    current_zone = current_zones[selected_index]
                    print(f"\n{self.BEGE}» Selecionado: {current_zone['name']}{self.RESET}")
                    lines_to_print += 2
            
            # Atualizar contador de linhas para próxima iteração
            last_lines_printed = lines_to_print - (3 if last_lines_printed == 0 else 0)  # Não recontar o box
            
            # Captura input
            key = self.get_key()
            
            if key == 'ESC':
                if search_term:
                    # Limpa pesquisa primeiro
                    search_term = ""
                    selected_index = 0
                else:
                    return None
            elif key == 'UP' and current_zones:
                selected_index = (selected_index - 1) % len(current_zones)
            elif key == 'DOWN' and current_zones:
                selected_index = (selected_index + 1) % len(current_zones)
            elif key == 'ENTER' and current_zones:
                return current_zones[selected_index]
            elif key == '\x7f' or key == '\b':  # Backspace
                if search_term:
                    search_term = search_term[:-1]
                    selected_index = 0
            elif len(key) == 1 and (key.isalnum() or key in ' -_.'):
                search_term += key.lower()
                selected_index = 0
        
    def _load_persisted_configs(self):
        """Carrega configurações persistidas do JSON"""
        # Carrega network_name
        network_name = self.config.get_network_name()
        if network_name and not getattr(self.args, 'network_name', None):
            self.args.network_name = network_name
            self.logger.info(f"Rede Docker carregada: {network_name}")
            
        # Carrega hostname  
        hostname = self.config.get_hostname()
        if hostname and not getattr(self.args, 'hostname', None):
            self.args.hostname = hostname
            self.logger.info(f"Hostname carregado: {hostname}")
    
    def get_user_input(self, prompt: str, required: bool = False, suggestion: str = None) -> str:
        """Coleta entrada do usuário com sugestão opcional"""
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
    
    def execute_module_instance(self, module_name: str, module_instance) -> bool:
        """Executa uma instância de módulo específico"""
        self.logger.info(f"Iniciando módulo: {module_name}")
        
        try:
            success = module_instance.run()
            if success:
                self.logger.info(f"Módulo {module_name} concluído com sucesso")
            else:
                self.logger.error(f"Módulo {module_name} falhou")
            return success
        except Exception as e:
            self.logger.error(f"Exceção no módulo {module_name}: {e}")
            return False

    def ensure_network_name(self) -> bool:
        """Garante que network_name esteja definido"""
        if getattr(self.args, 'network_name', None):
            return True
            
        network_name = self.config.get_network_name()
        if network_name:
            self.args.network_name = network_name
            return True
            
        self._print_section_box("🌐 DEFINIR REDE DOCKER", 40)
        if self.run_network_setup():
            return True
            
        self.logger.warning("Nome da rede não definido.")
        return False

    def _network_store_path(self) -> str:
        """Caminho do arquivo de persistência do nome da rede"""
        return "/root/dados_vps/dados_network"

    def _load_network_name(self) -> str:
        """Lê o network_name persistido (se existir)"""
        try:
            # 1) Tenta carregar do arquivo unificado do Orion
            dv = self._read_dados_vps_value("Rede interna:")
            if dv:
                return dv
            # 2) Fallback para arquivo dedicado
            path = self._network_store_path()
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Aceita formatos "network_name: valor" ou apenas "valor"
                    if content.startswith("network_name:"):
                        return content.split(":", 1)[1].strip()
                    return content if content else None
        except Exception:
            pass
        return None

    def _save_network_name(self, net: str) -> None:
        """Persiste o network_name para reutilização nas próximas execuções"""
        try:
            os.makedirs("/root/dados_vps", exist_ok=True)
            path = self._network_store_path()
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"network_name: {net}\n")
            self.logger.info(f"Rede Docker persistida em {path}")
            # Atualiza também o arquivo unificado do Orion
            self._upsert_dados_vps({"Rede interna:": net})
        except Exception as e:
            self.logger.warning(f"Falha ao persistir network_name: {e}")
    
    def _dados_vps_path(self) -> str:
        """Caminho do arquivo unificado de dados (padrão Orion)"""
        return "/root/dados_vps/dados_vps"
    
    def _read_dados_vps_value(self, label: str) -> str:
        """Lê um valor do arquivo dados_vps dado um rótulo (ex.: 'Nome do Servidor:' ou 'Rede interna:')"""
        try:
            path = self._dados_vps_path()
            if not os.path.isfile(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith(label):
                        # Extrai após 'label'
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            return parts[1].strip()
        except Exception:
            pass
        return None
    
    def _upsert_dados_vps(self, updates: dict) -> None:
        """Atualiza/inclui chaves no arquivo dados_vps preservando conteúdo"""
        try:
            os.makedirs("/root/dados_vps", exist_ok=True)
            path = self._dados_vps_path()
            lines = []
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            # Converte para dicionário por label -> índice
            idx_map = {}
            for i, ln in enumerate(lines):
                stripped = ln.strip()
                for key in updates.keys():
                    if stripped.startswith(key):
                        idx_map[key] = i
            # Aplica updates
            for key, value in updates.items():
                new_line = f"{key} {value}"
                if key in idx_map:
                    lines[idx_map[key]] = new_line
                else:
                    lines.append(new_line)
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
            self.logger.debug(f"dados_vps atualizado: {', '.join(updates.keys())}")
        except Exception as e:
            self.logger.debug(f"Falha ao atualizar dados_vps: {e}")

    def _hostname_store_path(self) -> str:
        """Caminho do arquivo de persistência do hostname"""
        return "/root/dados_vps/dados_hostname"

    def _load_hostname(self) -> str:
        """Lê o hostname persistido (se existir)"""
        try:
            # 1) Tenta carregar do arquivo unificado do Orion
            dv = self._read_dados_vps_value("Nome do Servidor:")
            if dv:
                return dv
            # 2) Fallback para arquivo dedicado
            path = self._hostname_store_path()
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith("hostname:"):
                        return content.split(":", 1)[1].strip()
                    return content if content else None
        except Exception:
            pass
        return None

    def _save_hostname(self, hostname: str) -> None:
        """Persiste o hostname para reutilização nas próximas execuções"""
        try:
            os.makedirs("/root/dados_vps", exist_ok=True)
            path = self._hostname_store_path()
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"hostname: {hostname}\n")
            self.logger.info(f"Hostname persistido em {path}")
            # Atualiza também o arquivo unificado do Orion
            self._upsert_dados_vps({"Nome do Servidor:": hostname})
        except Exception as e:
            self.logger.warning(f"Falha ao persistir hostname: {e}")
    
    def execute_module(self, module_name, **kwargs):
        """Executa um módulo específico por nome"""
        try:
            if module_name == 'basic':
                basic_setup = BasicSetup(config_manager=self.config)
                return basic_setup.run()
            
            
            elif module_name == 'docker':
                docker_setup = DockerSetup()
                return docker_setup.run()
            
            elif module_name == 'traefik':
                # Garante network_name e passa email
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Traefik.")
                    return True
                
                # Verifica se é dependência automática ou selecionado explicitamente
                is_auto_mode = hasattr(self, 'dependency_modules') and module_name in self.dependency_modules
                
                # Email será solicitado pelo próprio módulo se não fornecido
                traefik_setup = TraefikSetup(
                    email=kwargs.get('email') or self.args.email,
                    network_name=self.args.network_name,
                    config_manager=self.config,
                    auto_mode=is_auto_mode
                )
                return traefik_setup.run()
            
            elif module_name == 'portainer':
                # Garante network_name; domínio será solicitado se não fornecido
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Portainer.")
                    return True
                
                # Verifica se é dependência automática ou selecionado explicitamente
                is_auto_mode = hasattr(self, 'dependency_modules') and module_name in self.dependency_modules
                
                portainer_setup = PortainerSetup(
                    kwargs.get('portainer_domain') or self.args.portainer_domain,
                    network_name=self.args.network_name,
                    config_manager=self.config,
                    auto_mode=is_auto_mode
                )
                return portainer_setup.run()
            
            elif module_name == 'redis':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Redis.")
                    return True
                redis_setup = RedisSetup(network_name=self.args.network_name)
                return redis_setup.run()
            
            elif module_name == 'postgres':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do PostgreSQL.")
                    return True
                postgres_setup = PostgresSetup(network_name=self.args.network_name)
                return postgres_setup.run()
            
            elif module_name == 'pgvector':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do PgVector.")
                    return True
                pgvector_setup = PgVectorSetup(network_name=self.args.network_name)
                return pgvector_setup.run()
            
            elif module_name == 'minio':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do MinIO.")
                    return True
                minio_setup = MinioSetup(network_name=self.args.network_name)
                return minio_setup.run()
            
            elif module_name == 'chatwoot':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Chatwoot.")
                    return True
                chatwoot_setup = ChatwootSetup(network_name=self.args.network_name, config_manager=self.config)
                return chatwoot_setup.run()
            
            elif module_name == 'directus':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Directus.")
                    return True
                directus_setup = DirectusSetup(network_name=self.args.network_name)
                return directus_setup.run()
            
            elif module_name == 'passbolt':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Passbolt.")
                    return True
                passbolt_setup = PassboltSetup(network_name=self.args.network_name)
                return passbolt_setup.run()
            
            elif module_name == 'n8n':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do N8N.")
                    return True
                n8n_setup = N8NSetup(network_name=self.args.network_name, config_manager=self.config)
                return n8n_setup.run()
            
            elif module_name == 'grafana':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Grafana.")
                    return True
                grafana_setup = GrafanaSetup(network_name=self.args.network_name)
                return grafana_setup.run()
            
            elif module_name == 'gowa':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do GOWA.")
                    return True
                gowa_setup = GowaSetup(network_name=self.args.network_name)
                return gowa_setup.run()
            
            elif module_name == 'livchatbridge':
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do LivChatBridge.")
                    return True
                livchatbridge_setup = LivChatBridgeSetup(network_name=self.args.network_name)
                return livchatbridge_setup.run_setup()
            
            elif module_name == 'cleanup':
                cleanup_setup = CleanupSetup()
                return cleanup_setup.run()
            
            else:
                self.logger.error(f"Módulo '{module_name}' não encontrado")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao executar módulo {module_name}: {e}")
            return False
    
    def run_basic_setup(self) -> bool:
        """Executa setup básico"""
        basic_setup = BasicSetup(config_manager=self.config)
        return basic_setup.run()
    
    
    def run_docker_setup(self) -> bool:
        """Executa instalação do Docker"""
        docker_setup = DockerSetup(not self.args.no_swarm)
        return self.execute_module_instance("Docker", docker_setup)
    
    def run_traefik_setup(self, email: str) -> bool:
        """Executa instalação do Traefik"""
        # Garante que network_name esteja definido
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Traefik.")
            return True
        if not email:
            # Pergunta email interativamente
            print("\n--- Configuração de SSL/Traefik ---")
            email = self.get_user_input("Digite o email para certificados SSL (Enter para pular)")
            if not email:
                self.logger.warning("Email não fornecido, pulando instalação do Traefik")
                return True
            self.logger.info(f"Email configurado: {email}")
        
        traefik_setup = TraefikSetup(email=email, network_name=self.args.network_name, config_manager=self.config)
        return traefik_setup.run()
    
    def run_portainer_setup(self, domain: str) -> bool:
        """Executa instalação do Portainer"""
        # Garante que network_name esteja definido
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Portainer.")
            return True
        if not domain:
            # Pergunta domínio interativamente
            print("\n--- Configuração do Portainer ---")
            domain = self.get_user_input("Digite o domínio do Portainer (ex: portainer.seudominio.com, Enter para pular)")
            if not domain:
                self.logger.warning("Domínio não fornecido, pulando instalação do Portainer")
                return True
            self.logger.info(f"Domínio Portainer configurado: {domain}")
        
        portainer_setup = PortainerSetup(domain=domain, network_name=self.args.network_name, config_manager=self.config)
        return portainer_setup.run()

    def run_network_setup(self) -> bool:
        """Define ou altera o nome da rede Docker (network_name) de forma interativa"""
        self._print_section_box("🌐 DEFINIR REDE DOCKER", 50)
        
        atual = getattr(self.args, 'network_name', None)
        if atual:
            print(f"{self.BEGE}Rede atual: {self.BRANCO}{atual}{self.RESET}")
            print("")
        
        while True:
            prompt = "Nome da rede Docker (Enter para 'livchat_network' ou digite outro valor)"
            net = self.get_user_input(prompt, suggestion="livchat_network")
            if not net:
                print(f"{self.VERMELHO}Nome da rede é obrigatório. Tente novamente.{self.RESET}")
                continue
                
            # Validação simples: letras, números, hífen e underline, 2-50 chars
            import re
            if not re.match(r'^[A-Za-z0-9_-]{2,50}$', net):
                print(f"{self.VERMELHO}Nome inválido.{self.RESET} Use apenas letras, números, '-', '_' e entre 2 e 50 caracteres.")
                continue
                
            self.args.network_name = net
            self.logger.info(f"Rede Docker definida: {net}")
            
            # Persiste no ConfigManager
            self.config.set_network_name(net)
            
            print(f"{self.VERDE}✅ Rede Docker configurada: {self.BRANCO}{net}{self.RESET}")
            return True
    
    def resolve_dependencies(self, selected_modules: List[str], explicitly_selected: List[str] = None) -> List[str]:
        """Resolve dependências recursivamente e retorna lista ordenada de módulos para instalação"""
        if explicitly_selected is None:
            explicitly_selected = selected_modules.copy()
            
        required_modules = set()
        
        def add_dependencies_recursive(module: str):
            """Adiciona dependências de forma recursiva"""
            if module in required_modules:
                return
            required_modules.add(module)
            
            # Adiciona dependências do módulo atual
            deps = self.dependencies.get(module, [])
            for dep in deps:
                add_dependencies_recursive(dep)
        
        # Resolve dependências recursivamente para cada módulo selecionado
        for module in selected_modules:
            add_dependencies_recursive(module)
        
        # Se 'basic' está nas dependências mas não foi explicitamente selecionado
        # e as configurações básicas já estão completas, remove da lista
        if 'basic' in required_modules and 'basic' not in explicitly_selected:
            if self.is_basic_config_complete():
                required_modules.remove('basic')
                self.logger.info("Removendo 'basic' das dependências - configurações já completas")
        
        # Armazena quais módulos são dependências automáticas para o contexto
        self.dependency_modules = required_modules - set(explicitly_selected)
        
        # Ordena pelos módulos de infraestrutura primeiro
        ordered_modules = []
        
        # Primeiro, adiciona módulos de infraestrutura na ordem
        for module in self.install_order:
            if module in required_modules:
                ordered_modules.append(module)
                required_modules.remove(module)
        
        # Adiciona módulos restantes (aplicações)
        ordered_modules.extend(sorted(required_modules))
        
        return ordered_modules
    
    def is_basic_config_complete(self) -> bool:
        """Verifica se as configurações básicas essenciais já estão definidas"""
        try:
            # Verificar configurações essenciais
            user_email = self.config.get_user_email()
            network_name = self.config.get_network_name()
            
            # Se email e rede estão definidos, considera completo
            if user_email and network_name:
                self.logger.debug(f"Configuração básica já completa: email={user_email}, network={network_name}")
                return True
                
            return False
        except Exception as e:
            self.logger.debug(f"Erro ao verificar configuração básica: {e}")
            return False
    
    def collect_global_config(self):
        """Executa módulo de configuração global apenas se necessário"""
        # Se configuração básica já está completa, pula execução
        if self.is_basic_config_complete():
            self.logger.info("Configurações básicas já completas, pulando setup básico")
            return True
            
        basic_setup = BasicSetup(config_manager=self.config)
        return basic_setup.run()
    
    
    def run_multiple_modules(self, selected_modules: List[str]) -> bool:
        """Executa múltiplos módulos com resolução de dependências"""
        if not selected_modules:
            self.logger.warning("Nenhum módulo selecionado")
            return True
        
        # Se for apenas cleanup, não precisa de configurações globais
        if selected_modules == ['cleanup']:
            return self.execute_module('cleanup')
        
        # Verificar se 'basic' foi selecionado explicitamente pelo usuário
        basic_explicitly_selected = 'basic' in selected_modules
        
        # Se basic foi selecionado explicitamente, manter na lista para forçar execução
        if not basic_explicitly_selected:
            # Se basic não foi selecionado explicitamente, usar collect_global_config 
            # que verifica se já está completo antes de executar
            self.collect_global_config()
        else:
            # Basic foi selecionado explicitamente, remover da lista mas garantir execução
            selected_modules = [m for m in selected_modules if m != 'basic']
            # Forçar execução do BasicSetup mesmo se já configurado (reconfiguração)
            self.logger.info("Setup básico selecionado explicitamente - executando configuração")
            basic_setup = BasicSetup(config_manager=self.config)
            if not basic_setup.run():
                self.logger.error("Falha na configuração básica explícita")
                return False
        
        # Se não sobrou nenhum módulo além do basic, retorna sucesso
        if not selected_modules:
            self.logger.info("Configuração básica concluída. Nenhum módulo adicional selecionado.")
            return True
        
        # Resolve dependências (precisa manter referência dos módulos originalmente selecionados)
        original_selected = selected_modules.copy()
        if basic_explicitly_selected:
            original_selected.append('basic')  # Adiciona basic de volta para a lista de explicitamente selecionados
        ordered_modules = self.resolve_dependencies(selected_modules, original_selected)
        
        self._print_section_box("📋 ORDEM DE INSTALAÇÃO", 50)
        for i, module in enumerate(ordered_modules, 1):
            indicator = "🔹" if module in original_selected else "📦"
            print(f"{i:2d}. {indicator} {self.get_module_display_name(module)}")
        
        print(f"\n📦 = Dependência automática")
        print(f"🔹 = Selecionado pelo usuário")
        
        input(f"\n{self.BEGE}Pressione {self.VERDE}Enter{self.BEGE} para continuar ou {self.VERMELHO}Ctrl+C{self.BEGE} para cancelar...{self.RESET}")
        
        # Executa módulos em ordem
        failed_modules = []
        skipped_modules = []
        remaining_modules = ordered_modules.copy()
        
        for i, module in enumerate(ordered_modules, 1):
            # Verifica se este módulo deve ser pulado devido a dependências falhadas
            if module in skipped_modules:
                continue
                
            self._print_box_title(f"📋 Executando módulo {i}/{len(ordered_modules)}: {self.get_module_display_name(module)}", 80)
            
            success = self.execute_module(module)
            
            if success:
                self.logger.info(f"✅ Módulo {module} concluído com sucesso")
            else:
                self.logger.error(f"❌ Falha no módulo {module}")
                failed_modules.append(module)
                
                # Verifica se outros módulos dependem deste que falhou
                dependent_modules = self._get_dependent_modules(module, remaining_modules[i:])
                
                if dependent_modules:
                    skipped_modules.extend(dependent_modules)
                    self._handle_dependency_failure(module, dependent_modules)
                    
                    # Pergunta ao usuário se quer continuar com módulos restantes
                    if not self._ask_continue_after_dependency_failure(remaining_modules[i:], dependent_modules):
                        break
                
                if self.args.stop_on_error:
                    self.logger.error(f"Parando execução devido a falha em: {module}")
                    break
        
        # Resumo final
        self.show_installation_summary(ordered_modules, failed_modules, skipped_modules, original_selected)
        
        return len(failed_modules) == 0
    
    def _get_dependent_modules(self, failed_module: str, remaining_modules: List[str]) -> List[str]:
        """Encontra módulos que dependem do módulo falhado"""
        dependent_modules = []
        
        for module in remaining_modules:
            dependencies = self.dependencies.get(module, [])
            if failed_module in dependencies:
                dependent_modules.append(module)
                
        return dependent_modules
    
    def _handle_dependency_failure(self, failed_module: str, dependent_modules: List[str]):
        """Mostra erro de dependência com sugestões"""
        
        # Box de erro com estilo consistente
        self._print_section_box("⚠️ FALHA EM DEPENDÊNCIA CRÍTICA", 60)
        
        print(f"{self.VERMELHO}❌ MÓDULO FALHADO:{self.RESET}")
        print(f"   {self.get_module_display_name(failed_module)}")
        print()
        
        print(f"{self.LARANJA}🔗 MÓDULOS AFETADOS (serão pulados):{self.RESET}")
        for module in dependent_modules:
            print(f"   • {self.get_module_display_name(module)}")
        print()
        
        # Sugestões específicas baseadas no módulo falhado
        suggestions = self._get_failure_suggestions(failed_module)
        if suggestions:
            print(f"{self.BEGE}💡 SUGESTÕES PARA VERIFICAR:{self.RESET}")
            for suggestion in suggestions:
                print(f"   • {suggestion}")
            print()
    
    def _get_failure_suggestions(self, failed_module: str) -> List[str]:
        """Retorna sugestões específicas para cada tipo de falha"""
        suggestions_map = {
            'postgres': [
                'Verificar se Portainer está acessível e funcionando',
                'Confirmar credenciais do Portainer (senha pode ter sido alterada)',
                'Verificar conectividade de rede com o Portainer',
                'Tentar fazer login manual no Portainer via browser'
            ],
            'portainer': [
                'Verificar se Docker Swarm está ativo',
                'Confirmar se rede Docker foi criada corretamente',
                'Verificar conectividade de rede e DNS',
                'Verificar logs do Docker: docker service logs portainer_agent'
            ],
            'traefik': [
                'Verificar se Docker Swarm está ativo',
                'Confirmar configuração de DNS e certificados',
                'Verificar se portas 80 e 443 estão disponíveis',
                'Verificar logs do Traefik: docker service logs traefik'
            ],
            'docker': [
                'Verificar se sistema operacional é compatível',
                'Confirmar permissões de root',
                'Verificar conectividade com repositórios Docker',
                'Verificar espaço em disco disponível'
            ]
        }
        
        return suggestions_map.get(failed_module, [
            f'Verificar logs do sistema: tail -f /var/log/setup_inicial.log',
            f'Tentar executar apenas o módulo {failed_module} isoladamente',
            f'Verificar pré-requisitos do módulo {failed_module}'
        ])
    
    def _ask_continue_after_dependency_failure(self, remaining_modules: List[str], dependent_modules: List[str]) -> bool:
        """Pergunta se usuário quer continuar com módulos restantes"""
        
        # Calcula módulos que ainda podem ser executados (não afetados)
        unaffected_modules = [m for m in remaining_modules if m not in dependent_modules]
        
        if not unaffected_modules:
            print(f"{self.VERMELHO}Nenhum módulo restante pode ser executado.{self.RESET}")
            input(f"{self.BEGE}Pressione Enter para finalizar...{self.RESET}")
            return False
        
        print(f"{self.VERDE}MÓDULOS RESTANTES (não afetados):{self.RESET}")
        for module in unaffected_modules:
            print(f"   • {self.get_module_display_name(module)}")
        print()
        
        while True:
            print(f"{self.BEGE}Deseja continuar com os módulos restantes?{self.RESET}")
            print(f"{self.VERDE}Enter = Continuar{self.RESET} · {self.VERMELHO}N + Enter = Parar{self.RESET}")
            
            try:
                choice = input().strip().lower()
                if choice == '' or choice == 'y' or choice == 's':
                    return True
                elif choice == 'n' or choice == 'no' or choice == 'nao':
                    return False
                else:
                    print(f"{self.VERMELHO}Opção inválida. Digite Enter para continuar ou N para parar.{self.RESET}")
            except KeyboardInterrupt:
                return False

    def get_module_display_name(self, module: str) -> str:
        """Retorna nome amigável do módulo"""
        names = {
            'basic': 'Config (E-mail, Hostname, Cloudflare, Rede, Timezone)', 
            'docker': 'Instalação do Docker + Swarm',
            'traefik': 'Instalação do Traefik (Proxy Reverso)',
            'portainer': 'Instalação do Portainer (Gerenciador Docker)',
            'redis': 'Redis (Cache/Session Store)',
            'postgres': 'PostgreSQL (Banco Relacional)',
            'pgvector': 'PostgreSQL + PgVector (Banco Vetorial)',
            'minio': 'MinIO (S3 Compatible Storage)',
            'chatwoot': 'Chatwoot (Customer Support Platform)',
            'directus': 'Directus (Headless CMS)',
            'n8n': 'N8N (Workflow Automation)',
            'grafana': 'Grafana (Stack de Monitoramento)',
            'gowa': 'GOWA (WhatsApp API Multi Device)',
            'livchatbridge': 'LivChatBridge (Webhook Connector)',
            'passbolt': 'Passbolt (Password Manager)',
            'evolution': 'Evolution API v2 (WhatsApp API)',
            'cleanup': 'Limpeza Completa do Ambiente'
        }
        return names.get(module, module.title())
    
    def show_installation_summary(self, all_modules: List[str], failed_modules: List[str], skipped_modules: List[str], selected_modules: List[str]):
        """Exibe resumo da instalação"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        successful_modules = len(all_modules) - len(failed_modules) - len(skipped_modules)
        
        self._print_box_title("📊 RESUMO DA INSTALAÇÃO", 80)
        print(f"⏱️  Tempo total: {total_time:.1f}s")
        print(f"📦 Módulos instalados: {successful_modules}/{len(all_modules)}")
        print(f"🎯 Selecionados pelo usuário: {len(selected_modules)}")
        print(f"🔗 Dependências automáticas: {len(all_modules) - len(selected_modules)}")
        
        if failed_modules:
            print(f"\n❌ MÓDULOS COM FALHA:")
            for module in failed_modules:
                print(f"   • {self.get_module_display_name(module)}")
                
        if skipped_modules:
            print(f"\n⏭️ MÓDULOS PULADOS (dependências falharam):")
            for module in skipped_modules:
                print(f"   • {self.get_module_display_name(module)}")
        
        if not failed_modules and not skipped_modules:
            print(f"\n✅ TODOS OS MÓDULOS INSTALADOS COM SUCESSO!")
        elif successful_modules > 0:
            print(f"\n✅ {successful_modules} módulo(s) instalado(s) com sucesso!")
            
        # Exibe informações úteis
        config_summary = self.config.get_summary()
        if config_summary["total_apps"] > 0:
            print(f"\n🔧 CONFIGURAÇÕES:")
            print(f"   • Aplicações configuradas: {config_summary['total_apps']}")
            print(f"   • DNS automático: {'✅' if config_summary['auto_dns_enabled'] else '❌'}")
            print(f"   • Network Docker: {config_summary['network_name']}")
            
        print(f"\n📁 Configurações salvas em: /root/livchat-config.json")
    
    def run_redis_setup(self) -> bool:
        """Executa instalação do Redis"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Redis.")
            return True
        redis_setup = RedisSetup(network_name=self.args.network_name)
        return redis_setup.run()
    
    def run_postgres_setup(self) -> bool:
        """Executa instalação do PostgreSQL"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do PostgreSQL.")
            return True
        postgres_setup = PostgresSetup(network_name=self.args.network_name)
        return postgres_setup.run()
    
    def run_pgvector_setup(self) -> bool:
        """Executa instalação do PostgreSQL + PgVector"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do PgVector.")
            return True
        pgvector_setup = PgVectorSetup(network_name=self.args.network_name)
        return pgvector_setup.run()
    
    def run_minio_setup(self) -> bool:
        """Executa instalação do MinIO (S3)"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do MinIO.")
            return True
        minio_setup = MinioSetup(network_name=self.args.network_name)
        return minio_setup.run()
    
    def run_chatwoot_setup(self) -> bool:
        """Executa setup do Chatwoot"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Chatwoot.")
            return True
        chatwoot_setup = ChatwootSetup(network_name=self.args.network_name, config_manager=self.config)
        return chatwoot_setup.run()
    
    def run_directus_setup(self) -> bool:
        """Executa setup do Directus"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Directus.")
            return True
        directus_setup = DirectusSetup(network_name=self.args.network_name)
        return directus_setup.run()
    
    def run_passbolt_setup(self) -> bool:
        """Executa setup do Passbolt"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Passbolt.")
            return True
        passbolt_setup = PassboltSetup(network_name=self.args.network_name)
        return passbolt_setup.run()
    
    def run_n8n_setup(self) -> bool:
        """Executa setup do N8N"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do N8N.")
            return True
        n8n_setup = N8NSetup(network_name=self.args.network_name, config_manager=self.config)
        return n8n_setup.run()
    
    def run_grafana_setup(self) -> bool:
        """Executa setup do Grafana"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do Grafana.")
            return True
        grafana_setup = GrafanaSetup(network_name=self.args.network_name)
        return grafana_setup.run()
    
    def run_gowa_setup(self) -> bool:
        """Executa setup do GOWA"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do GOWA.")
            return True
        gowa_setup = GowaSetup(network_name=self.args.network_name)
        return gowa_setup.run()
    
    def run_livchatbridge_setup(self) -> bool:
        """Executa setup do LivChatBridge"""
        if not self.ensure_network_name():
            self.logger.warning("Nome da rede não definido. Pulando instalação do LivChatBridge.")
            return True
        livchatbridge_setup = LivChatBridgeSetup(network_name=self.args.network_name)
        return livchatbridge_setup.run_setup()
    
    def run_cleanup_setup(self) -> bool:
        """Executa limpeza completa"""
        # Deixe a confirmação ser feita pelo próprio módulo CleanupSetup
        cleanup_setup = CleanupSetup()
        return cleanup_setup.run()
    
    def get_module_map(self) -> dict:
        """Retorna mapeamento de módulos disponíveis"""
        return {
            'basic': ('Setup Básico', lambda: self.run_basic_setup()),
            'docker': ('Docker', lambda: self.run_docker_setup()),
            'traefik': ('Traefik', lambda: self.run_traefik_setup(self.args.email)),
            'portainer': ('Portainer', lambda: self.run_portainer_setup(self.args.portainer_domain)),
            'redis': ('Redis', lambda: self.run_redis_setup()),
            'postgres': ('PostgreSQL', lambda: self.run_postgres_setup()),
            'pgvector': ('PostgreSQL + PgVector', lambda: self.run_pgvector_setup()),
            'minio': ('MinIO (S3)', lambda: self.run_minio_setup()),
            'chatwoot': ('Chatwoot', lambda: self.run_chatwoot_setup()),
            'directus': ('Directus', lambda: self.run_directus_setup()),
            'passbolt': ('Passbolt', lambda: self.run_passbolt_setup()),
            'n8n': ('N8N', lambda: self.run_n8n_setup()),
            'grafana': ('Grafana', lambda: self.run_grafana_setup()),
            'gowa': ('GOWA', lambda: self.run_gowa_setup()),
            'livchatbridge': ('LivChatBridge', lambda: self.run_livchatbridge_setup()),
            'cleanup': ('Limpeza', lambda: self.run_cleanup_setup())
        }
    
    def run_modules(self) -> bool:
        """Executa módulos baseado nos argumentos"""
        module_map = self.get_module_map()
        failed_modules = []
        
        if self.args.module:
            # Executa módulo específico
            if self.args.module in module_map:
                module_name, module_func = module_map[self.args.module]
                success = module_func()
                if not success:
                    failed_modules.append(module_name)
            else:
                self.logger.error(f"Módulo desconhecido: {self.args.module}")
                return False
        else:
            # Executa módulos principais (exceto cleanup)
            main_modules = ['basic', 'docker', 'traefik', 'portainer', 'redis', 'postgres', 'pgvector', 'minio']
            
            for module_key in main_modules:
                if module_key in module_map:
                    module_name, module_func = module_map[module_key]
                    success = module_func()
                    if not success:
                        failed_modules.append(module_name)
                        if self.args.stop_on_error:
                            self.logger.error(f"Parando execução devido a falha em: {module_name}")
                            break
        
        return len(failed_modules) == 0
    
    def run_evolution_setup(self) -> bool:
        """Executa setup da Evolution API v2"""
        try:
            setup = EvolutionSetup(network_name=self.args.network_name)
            return setup.run()
        except Exception as e:
            self.logger.error(f"Erro no setup da Evolution API: {e}")
            return False
    
    def show_summary(self, success: bool) -> None:
        """Exibe resumo da execução"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if success:
            self.logger.info(f"Setup concluído com sucesso ({duration:.2f}s)")
            self.logger.info("Próximas etapas: Portainer, Traefik, aplicações")
        else:
            self.logger.error(f"Setup concluído com falhas ({duration:.2f}s)")
