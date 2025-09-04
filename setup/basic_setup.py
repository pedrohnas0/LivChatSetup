#!/usr/bin/env python3
"""
Módulo de Configuração Global - Config Setup
Baseado no BaseSetup - Coleta email, DNS, rede e timezone
"""

import os
import sys
import shutil
import termios
import tty

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup.base_setup import BaseSetup
from utils.config_manager import ConfigManager

class BasicSetup(BaseSetup):
    """Setup Básico Completo - Sistema, Config Global, Email, Cloudflare, Rede, Timezone"""
    
    # Cores para interface (seguindo padrão do projeto)
    LARANJA = "\033[38;5;173m"  # Orange - Para ASCII art e highlights
    VERDE = "\033[32m"          # Green - Para success states e selected items
    BRANCO = "\033[97m"         # Bright white - Para focus states e headings
    BEGE = "\033[93m"           # Beige - Para informational text e legends
    VERMELHO = "\033[91m"       # Red - Para errors e warnings
    CINZA = "\033[90m"          # Gray - Para borders e inactive items
    RESET = "\033[0m"           # Reset - Always close color sequences
    
    def __init__(self, config_manager: ConfigManager = None):
        super().__init__("Config (E-mail, Hostname, Cloudflare, Rede, Timezone)")
        self.config = config_manager or ConfigManager()
    
    def _get_terminal_width(self) -> int:
        """Obtém largura do terminal de forma segura"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80  # Fallback
    
    def _print_ascii_config(self):
        """Exibe ASCII art CONFIG"""
        terminal_width = self._get_terminal_width()
        box_width = min(101, terminal_width - 4)
        line = "─" * (box_width - 1)
        
        print(f"{self.CINZA}╭{line}╮{self.RESET}")
        print(f"{self.CINZA}│{' ' * (box_width - 1)}{self.CINZA}│{self.RESET}")
        
        # ASCII art CONFIG
        ascii_lines = [
            "██████╗ ██████╗ ███╗   ██╗███████╗██╗ ██████╗ ",
            "██╔════╝██╔═══██╗████╗  ██║██╔════╝██║██╔════╝ ",
            "██║     ██║   ██║██╔██╗ ██║█████╗  ██║██║  ███╗",
            "██║     ██║   ██║██║╚██╗██║██╔══╝  ██║██║   ██║",
            "╚██████╗╚██████╔╝██║ ╚████║██║     ██║╚██████╔╝",
            " ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚═╝ ╚═════╝ "
        ]
        
        for line_content in ascii_lines:
            content_width = box_width - 1
            centered_content = line_content.center(content_width)
            colored_content = f"{self.LARANJA}{line_content}{self.RESET}"
            colored_line = centered_content.replace(line_content, colored_content)
            print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        
        print(f"{self.CINZA}│{' ' * (box_width - 1)}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
        print()
    
    def _print_box_title(self, title: str, width: int = None):
        """Cria box com título seguindo padrão do projeto"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(80, terminal_width - 4)
        
        # Remove códigos de cor para calcular tamanho real
        import re
        clean_title = re.sub(r'\033\[[0-9;]*m', '', title)
        
        line = "─" * (width - 1)
        print(f"{self.CINZA}╭{line}╮{self.RESET}")
        
        # Centralização perfeita usando Python
        content_width = width - 2
        centered_clean = clean_title.center(content_width)
        
        # Aplicar cor laranja ao título centralizado
        colored_title = f"{self.LARANJA}{clean_title}{self.RESET}"
        colored_line = centered_clean.replace(clean_title, colored_title)
            
        print(f"{self.CINZA}│{colored_line}{self.CINZA}│{self.RESET}")
        print(f"{self.CINZA}╰{line}╯{self.RESET}")
    
    def _print_section_box(self, title: str, width: int = None):
        """Cria box de seção menor"""
        if width is None:
            terminal_width = self._get_terminal_width()
            width = min(60, terminal_width - 10)
        
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
    
    def _clear_lines(self, count: int):
        """Limpa linhas específicas em vez de limpar toda a tela"""
        for _ in range(count):
            print("\033[F\033[K", end="")  # Move cursor up e limpa linha
    
    def select_cloudflare_zone(self, zones) -> dict:
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
    
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para configuração"""
        if not self.check_root():
            return False
        
        # Verifica se ConfigManager está funcionando
        try:
            self.config.get_user_email()
            return True
        except Exception as e:
            self.logger.error(f"Erro no ConfigManager: {e}")
            return False
    
    def configure_email(self) -> bool:
        """Configura email padrão do usuário"""
        self.log_step_start("Configuração de email")
        
        current_email = self.config.get_user_email()
        if not current_email:
            email = self.get_user_input("Digite seu email padrão (será usado para SSL e apps)", required=True)
            if email:
                self.config.set_user_email(email)
                self.logger.info(f"Email configurado: {email}")
            else:
                self.logger.warning("Email não configurado")
                return False
        else:
            print(f"📧 Email padrão: {current_email}")
            self.logger.info(f"Email já configurado: {current_email}")
        
        self.log_step_complete("Configuração de email")
        return True
    
    def configure_cloudflare_dns(self) -> bool:
        """Configura DNS automático via Cloudflare"""
        self.log_step_start("Configuração DNS Cloudflare")
        
        # Verificar configuração DNS existente
        if self.config.is_cloudflare_auto_dns_enabled():
            # Mostrar configuração atual
            cloudflare_config = self.config.get_cloudflare_config()
            zone_name = cloudflare_config.get('zone_name', 'N/A')
            subdomain = self.config.get_default_subdomain() or 'nenhum'
            
            self._print_section_box("🌐 CLOUDFLARE CONFIGURADO")
            print(f"{self.VERDE}✅ DNS automático ativo{self.RESET}")
            print(f"{self.BEGE}Zona: {self.BRANCO}{zone_name}{self.RESET}")
            print(f"{self.BEGE}Subdomínio padrão: {self.BRANCO}{subdomain}{self.RESET}")
            
            reconfigure = input(f"\n{self.BEGE}{self.VERDE}Enter{self.RESET}{self.BEGE} para manter ou digite {self.VERDE}'s'{self.RESET}{self.BEGE} para reconfigurar:{self.RESET} ").strip().lower()
            if reconfigure == 's':
                return self._setup_cloudflare_from_scratch()
        else:
            # Configurar pela primeira vez
            self._print_section_box("🌐 GERENCIAMENTO DNS AUTOMÁTICO", 50)
            print("O sistema pode gerenciar automaticamente os registros DNS via Cloudflare.")
            print("🔒 Suas credenciais ficam seguras e armazenadas apenas localmente.")
            
            dns_choice = input("\nDeseja configurar gerenciamento automático de DNS? (s/N): ").strip().lower()
            
            if dns_choice == 's':
                return self._setup_cloudflare_from_scratch()
            else:
                print("Prosseguindo sem gerenciamento DNS automático.")
        
        self.log_step_complete("Configuração DNS Cloudflare")
        return True
    
    def _setup_cloudflare_from_scratch(self) -> bool:
        """Configura Cloudflare do zero"""
        self._print_section_box("🌐 CONFIGURAÇÃO CLOUDFLARE DNS")
        
        # Email do Cloudflare
        current_email = self.config.get_user_email()
        cf_email_suggestion = f"Enter para '{current_email}' ou digite outro email" if current_email else "Digite o email da sua conta Cloudflare"
        cf_email = self.get_user_input(f"Email Cloudflare ({cf_email_suggestion})")
        if not cf_email and current_email:
            cf_email = current_email
        
        if not cf_email:
            print("Email é obrigatório. Configuração cancelada.")
            return False
        
        # API Key do Cloudflare
        api_key = self.get_user_input("Digite sua Cloudflare API Key", required=True)
        
        if not api_key:
            print("API Key é obrigatória. Configuração cancelada.")
            return False
        
        # Lista e seleciona zona via Cloudflare API
        return self._setup_cloudflare_zone(cf_email, api_key)
    
    def _setup_cloudflare_zone(self, email: str, api_key: str) -> bool:
        """Configura zona Cloudflare com seleção interativa"""
        try:
            from utils.cloudflare_api import CloudflareAPI
            
            # Cria instância temporária para listar zonas
            temp_cf = CloudflareAPI(logger=self.logger)
            temp_cf.api_key = api_key
            temp_cf.email = email
            temp_cf.headers = {
                "X-Auth-Email": email,
                "X-Auth-Key": api_key,
                "Content-Type": "application/json"
            }
            
            # Lista zonas disponíveis
            print("\n🔍 Buscando suas zonas DNS...")
            zones = temp_cf.list_zones()
            if not zones:
                print("❌ Falha ao conectar com Cloudflare ou nenhuma zona encontrada")
                print("Verifique seu email e API Key e tente novamente.")
                return False
            
            # Usar menu scrollable para seleção de zona
            print(f"\n📋 {len(zones)} zonas encontradas - Use ↑/↓ para navegar:")
            selected_zone = self.select_cloudflare_zone(zones)
            
            if not selected_zone:
                print("\n❌ Configuração cancelada pelo usuário.")
                return False
            
            zone_name = selected_zone['name']
            zone_id = selected_zone['id']
            print(f"\n✅ Zona selecionada: {zone_name}")
            
            # Subdomínio padrão (opcional)
            subdomain = self.get_user_input("Digite um subdomínio padrão (ex: dev, Enter para sem subdomínio)")
            
            if subdomain:
                self.config.set_default_subdomain(subdomain)
                print(f"✅ Subdomínio padrão configurado: {subdomain}")
                print(f"   Exemplo de domínios: ptn.{subdomain}.{zone_name}")
            else:
                print(f"✅ Sem subdomínio padrão (domínios diretos)")
                print(f"   Exemplo de domínios: ptn.{zone_name}")
            
            # Salva configuração com email (necessário para Global API Key)
            self.config.set_cloudflare_config(api_key, zone_id, zone_name, email)
            self.config.set_cloudflare_auto_dns(True)
            
            print("✅ Cloudflare configurado com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na configuração Cloudflare: {e}")
            return False
    
    def configure_network(self) -> bool:
        """Configura nome da rede Docker"""
        self.log_step_start("Configuração de rede Docker")
        
        network_name = self.config.get_network_name()
        if network_name:
            print(f"🌐 Rede Docker: {network_name}")
            self.logger.info(f"Rede já configurada: {network_name}")
        else:
            self._print_section_box("🌐 DEFINIR REDE DOCKER", 50)
            
            while True:
                prompt = "Nome da rede Docker"
                net = self.get_user_input(prompt, suggestion="livchat_network")
                if not net:
                    print(f"{self.VERMELHO}Nome da rede é obrigatório. Tente novamente.{self.RESET}")
                    continue
                    
                # Validação simples
                import re
                if not re.match(r'^[A-Za-z0-9_-]{2,50}$', net):
                    print(f"{self.VERMELHO}Nome inválido.{self.RESET} Use apenas letras, números, '-', '_' e entre 2 e 50 caracteres.")
                    continue
                    
                self.config.set_network_name(net)
                self.logger.info(f"Rede Docker definida: {net}")
                print(f"{self.VERDE}✅ Rede Docker configurada: {self.BRANCO}{net}{self.RESET}")
                break
        
        self.log_step_complete("Configuração de rede Docker")
        return True
    
    def configure_hostname(self) -> bool:
        """Configura hostname do servidor"""
        self.log_step_start("Configuração de hostname")
        
        # Verificar hostname atual
        current_hostname = self._get_current_hostname()
        if current_hostname:
            # Usar padrão de sugestão como os outros campos
            hostname = self.get_user_input("Hostname do servidor", suggestion=current_hostname)
            
            if hostname and hostname != current_hostname:
                # Validar e aplicar novo hostname
                if self._validate_hostname_format(hostname):
                    if self._set_hostname(hostname):
                        if self._update_hosts_file(hostname):
                            # Persistir no config
                            self.config.set_hostname(hostname)
                            self.logger.info(f"Hostname configurado: {hostname}")
                            print(f"{self.VERDE}✅ Hostname alterado: {self.BRANCO}{current_hostname}{self.RESET} → {self.BRANCO}{hostname}{self.RESET}")
                        else:
                            self.logger.warning("Falha ao atualizar /etc/hosts, mas hostname foi configurado")
                            # Persistir mesmo se /etc/hosts falhou
                            self.config.set_hostname(hostname)
                    else:
                        self.logger.error("Falha ao configurar hostname")
                        return False
                else:
                    print(f"{self.VERMELHO}Formato inválido.{self.RESET} Use apenas letras, números e hífens (a-z, 0-9, -).")
                    return False
            else:
                # Manteve o hostname atual
                self.logger.info(f"Hostname mantido: {current_hostname}")
        else:
            # Não tem hostname, solicitar (opcional)
            hostname = self.get_user_input("Hostname do servidor (opcional)")
            if hostname:
                if self._validate_hostname_format(hostname):
                    if self._set_hostname(hostname):
                        if self._update_hosts_file(hostname):
                            # Persistir no config
                            self.config.set_hostname(hostname)
                            self.logger.info(f"Hostname configurado: {hostname}")
                            print(f"{self.VERDE}✅ Hostname configurado: {self.BRANCO}{hostname}{self.RESET}")
                        else:
                            self.logger.warning("Falha ao atualizar /etc/hosts, mas hostname foi configurado")
                            # Persistir mesmo se /etc/hosts falhou
                            self.config.set_hostname(hostname)
                    else:
                        self.logger.error("Falha ao configurar hostname")
                        return False
                else:
                    print(f"{self.VERMELHO}Formato inválido.{self.RESET} Use apenas letras, números e hífens (a-z, 0-9, -).")
                    return False
            else:
                self.logger.info("Configuração de hostname pulada")
        
        self.log_step_complete("Configuração de hostname")
        return True
    
    def _get_current_hostname(self) -> str:
        """Obtém o hostname atual"""
        try:
            import subprocess
            result = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Erro ao obter hostname atual: {e}")
        return ""
    
    def _validate_hostname_format(self, hostname: str) -> bool:
        """Valida o formato do hostname (RFC 1123)"""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        return re.match(pattern, hostname) is not None
    
    def _set_hostname(self, hostname: str) -> bool:
        """Define o hostname do sistema"""
        return self.run_command(f"hostnamectl set-hostname {hostname}", "configuração do hostname")
    
    def _update_hosts_file(self, hostname: str) -> bool:
        """Atualiza o arquivo /etc/hosts com o novo hostname"""
        hosts_file = "/etc/hosts"
        
        try:
            # Lê o arquivo atual
            with open(hosts_file, 'r') as f:
                content = f.read()
            
            # Backup do arquivo original
            from datetime import datetime
            backup_file = f"{hosts_file}.backup.{int(datetime.now().timestamp())}"
            with open(backup_file, 'w') as f:
                f.write(content)
            self.logger.debug(f"Backup criado: {backup_file}")
            
            # Atualiza a linha do localhost
            import re
            pattern = r'^127\.0\.0\.1\s+.*$'
            new_line = f"127.0.0.1 {hostname} localhost"
            
            lines = content.split('\n')
            updated = False
            
            for i, line in enumerate(lines):
                if re.match(pattern, line.strip()):
                    lines[i] = new_line
                    updated = True
                    self.logger.debug(f"Linha atualizada: {new_line}")
                    break
            
            # Se não encontrou a linha, adiciona
            if not updated:
                lines.insert(0, new_line)
                self.logger.debug(f"Linha adicionada: {new_line}")
            
            # Escreve o arquivo atualizado
            with open(hosts_file, 'w') as f:
                f.write('\n'.join(lines))
            
            self.logger.info("Arquivo /etc/hosts atualizado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar /etc/hosts: {e}")
            return False
    
    def update_system(self) -> bool:
        """Atualiza o sistema"""
        self.log_step_start("Atualização do sistema")
        
        # Verificar espaço em disco
        self.run_command("df -h / | tail -1 | awk '{print $4}'", "verificação de espaço", critical=False)
        
        # Update da lista de pacotes
        if not self.run_command("apt-get update", "atualização da lista de pacotes"):
            return False
            
        # Upgrade do sistema
        if not self.run_command("apt upgrade -y", "upgrade dos pacotes"):
            return False
        
        self.log_step_complete("Atualização do sistema")
        return True
    
    def configure_timezone(self) -> bool:
        """Configura timezone para São Paulo"""
        self.log_step_start("Configuração de timezone")
        
        # Verificar timezone atual
        import subprocess
        current_tz = subprocess.run("timedatectl show --property=Timezone --value", shell=True, capture_output=True, text=True)
        if current_tz.returncode == 0:
            current = current_tz.stdout.strip()
            self.logger.debug(f"Timezone atual: {current}")
            
            if current == "America/Sao_Paulo":
                self.logger.info("Timezone já configurado")
                self.log_step_complete("Configuração de timezone")
                return True
        
        # Configurar novo timezone
        if self.run_command("timedatectl set-timezone America/Sao_Paulo", "configuração do timezone"):
            # Verificar aplicação
            verify_result = subprocess.run("timedatectl show --property=Timezone --value", shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                new_tz = verify_result.stdout.strip()
                if new_tz == "America/Sao_Paulo":
                    self.logger.info(f"Timezone alterado para: {new_tz}")
                    self.log_step_complete("Configuração de timezone")
                    return True
                else:
                    self.logger.error(f"Timezone incorreto. Esperado: America/Sao_Paulo, Atual: {new_tz}")
            else:
                self.logger.error("Não foi possível verificar timezone")
        
        return False
    
    def install_basic_packages(self) -> bool:
        """Instala pacotes básicos necessários"""
        self.log_step_start("Instalação de pacotes básicos")
        
        packages = [
            ("apt-utils", "Utilitários do APT"),
            ("apparmor-utils", "Utilitários do AppArmor")
        ]
        
        success_count = 0
        total_packages = len(packages)
        
        for i, (package, description) in enumerate(packages, 1):
            self.logger.info(f"Pacote {i}/{total_packages}: {package}")
            self.logger.debug(f"Descrição: {description}")
            
            # Verificar se já instalado
            installed, version = self.check_package_installed(package)
            if installed:
                self.logger.info(f"Já instalado: {package} v{version}")
                success_count += 1
                continue
            
            # Instalar pacote
            if self.run_command(f"apt-get install -y {package}", f"instalação {package}"):
                success_count += 1
                # Verificar versão instalada
                installed, version = self.check_package_installed(package)
                if installed:
                    self.logger.info(f"Instalado: {package} v{version}")
            else:
                self.logger.error(f"Falha: {package}")
        
        # Atualizar cache
        if self.run_command("apt-get update", "atualização do cache"):
            self.logger.info(f"Pacotes instalados: {success_count}/{total_packages}")
        else:
            self.logger.warning("Falha ao atualizar cache")
            
        self.log_step_complete("Instalação de pacotes básicos")
        return success_count == total_packages
    
    def run(self) -> bool:
        """Executa setup básico completo - Sistema + Configurações"""
        self.logger.info(f"Iniciando {self.name}")
        
        if not self.validate_prerequisites():
            return False
        
        # Exibe ASCII art
        self._print_ascii_config()
        
        # Título principal
        self._print_box_title("🚀 SETUP BÁSICO LIVCHAT")
        
        try:
            # 1. Atualizar sistema
            if not self.update_system():
                self.logger.warning("Falha na atualização do sistema, continuando...")
            
            # 2. Configurar timezone
            if not self.configure_timezone():
                self.logger.warning("Falha na configuração de timezone, continuando...")
            
            # 3. Instalar pacotes básicos
            if not self.install_basic_packages():
                self.logger.warning("Falha na instalação de pacotes básicos, continuando...")
            
            # 4. Configurar email
            if not self.configure_email():
                return False
            
            # 5. Configurar hostname
            if not self.configure_hostname():
                self.logger.warning("Falha na configuração de hostname, continuando...")
            
            # 6. Configurar DNS Cloudflare
            if not self.configure_cloudflare_dns():
                return False
            
            # 7. Configurar rede Docker
            if not self.configure_network():
                return False
            
            # Resumo final
            self._print_section_box("✅ SETUP BÁSICO CONCLUÍDO")
            config_summary = self.config.get_summary()
            current_hostname = self._get_current_hostname()
            print(f"📧 Email: {config_summary.get('user_email', 'N/A')}")
            print(f"🖥️  Hostname: {current_hostname if current_hostname else 'N/A'}")
            print(f"🌐 DNS automático: {'✅' if config_summary.get('auto_dns_enabled') else '❌'}")
            print(f"🐳 Rede Docker: {config_summary.get('network_name', 'N/A')}")
            print(f"⏰ Timezone: America/Sao_Paulo")
            print(f"📦 Pacotes básicos instalados")
            
            duration = self.get_duration()
            self.logger.info(f"{self.name} concluído com sucesso ({duration:.2f}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante setup básico: {e}")
            return False
    
    def run_basic_setup(self) -> bool:
        """Método de compatibilidade - chama run()"""
        return self.run()