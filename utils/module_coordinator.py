#!/usr/bin/env python3
"""
Coordenador de Módulos
Simplifica a execução e gerenciamento dos módulos de setup
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import setup_logging
from setup.basic_setup import SystemSetup as BasicSetup
from setup.hostname_setup import HostnameSetup
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

class ModuleCoordinator:
    """Coordenador simplificado dos módulos de setup"""
    
    def __init__(self, args):
        self.args = args
        self.logger = setup_logging()
        self.start_time = datetime.now()
        # Carrega network_name persistido, se existir
        persisted = self._load_network_name()
        if persisted and not getattr(self.args, 'network_name', None):
            self.args.network_name = persisted
            self.logger.info(f"Rede Docker carregada do cache: {persisted}")
        # Carrega hostname persistido, se existir
        h_persisted = self._load_hostname()
        if h_persisted and not getattr(self.args, 'hostname', None):
            self.args.hostname = h_persisted
            self.logger.info(f"Hostname carregado do cache: {h_persisted}")
        
    def get_user_input(self, prompt: str, required: bool = False) -> str:
        """Coleta entrada do usuário de forma interativa"""
        try:
            value = input(f"{prompt}: ").strip()
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
        """Garante que self.args.network_name esteja definido, carregando persistido ou perguntando uma única vez"""
        # 1) Já definido via args
        if getattr(self.args, 'network_name', None):
            return True
        # 2) Tentar carregar persistido
        persisted = self._load_network_name()
        if persisted:
            self.args.network_name = persisted
            self.logger.info(f"Rede Docker carregada do cache: {persisted}")
            return True
        # 3) Perguntar uma única vez e salvar
        print("\n--- Definir Rede Docker ---")
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
                basic_setup = BasicSetup()
                return basic_setup.run_basic_setup()
            
            elif module_name == 'hostname':
                # Resolve hostname a partir de kwargs, args, cache unificado/dedicado
                provided = kwargs.get('hostname') or self.args.hostname or self._load_hostname()
                hostname_setup = HostnameSetup(provided)
                success = hostname_setup.run()
                if success:
                    final_hn = hostname_setup.hostname
                    if final_hn:
                        self.args.hostname = final_hn
                        self._save_hostname(final_hn)
                return success
            
            elif module_name == 'docker':
                docker_setup = DockerSetup()
                return docker_setup.run()
            
            elif module_name == 'traefik':
                # Garante network_name e passa email
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Traefik.")
                    return True
                # Email será solicitado pelo próprio módulo se não fornecido
                traefik_setup = TraefikSetup(
                    email=kwargs.get('email') or self.args.email,
                    network_name=self.args.network_name
                )
                return traefik_setup.run()
            
            elif module_name == 'portainer':
                # Garante network_name; domínio será solicitado se não fornecido
                if not self.ensure_network_name():
                    self.logger.warning("Nome da rede não definido. Pulando instalação do Portainer.")
                    return True
                portainer_setup = PortainerSetup(
                    kwargs.get('portainer_domain') or self.args.portainer_domain,
                    network_name=self.args.network_name
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
                chatwoot_setup = ChatwootSetup(network_name=self.args.network_name)
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
                n8n_setup = N8NSetup(network_name=self.args.network_name)
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
        basic_setup = BasicSetup()
        return basic_setup.run_basic_setup()
    
    def run_hostname_setup(self, hostname: str) -> bool:
        """Executa configuração de hostname (carrega cache, pergunta se necessário, e persiste)"""
        # Resolve hostname (args -> unificado -> dedicado -> None)
        resolved = hostname or getattr(self.args, 'hostname', None) or self._load_hostname()
        hostname_setup = HostnameSetup(resolved)
        success = self.execute_module_instance("Hostname", hostname_setup)
        if success:
            final_hn = hostname_setup.hostname
            if final_hn:
                self.args.hostname = final_hn
                self._save_hostname(final_hn)
        return success
    
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
        
        traefik_setup = TraefikSetup(email=email, network_name=self.args.network_name)
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
        
        portainer_setup = PortainerSetup(domain=domain, network_name=self.args.network_name)
        return portainer_setup.run()

    def run_network_setup(self) -> bool:
        """Define ou altera o nome da rede Docker (network_name) de forma interativa"""
        print("\n=== Definir Rede Docker (network_name) ===")
        atual = getattr(self.args, 'network_name', None)
        if atual:
            print(f"Rede atual: {atual}")
        while True:
            net = self.get_user_input("Digite o nome da rede Docker (ex: my_stack_net)")
            if not net:
                print("Nome da rede é obrigatório. Tente novamente.")
                continue
            # Validação simples: letras, números, hífen e underline, 2-50 chars
            import re
            if not re.match(r'^[A-Za-z0-9_-]{2,50}$', net):
                print("Nome inválido. Use apenas letras, números, '-', '_' e entre 2 e 50 caracteres.")
                continue
            self.args.network_name = net
            self.logger.info(f"Rede Docker definida: {net}")
            # Persiste imediatamente para todas as stacks
            self._save_network_name(net)
            return True
        
        # Não alcançável
        # return False
    
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
        chatwoot_setup = ChatwootSetup(network_name=self.args.network_name)
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
        n8n_setup = N8NSetup(network_name=self.args.network_name)
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
            'hostname': ('Hostname', lambda: self.run_hostname_setup(self.args.hostname)),
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
            main_modules = ['basic', 'hostname', 'docker', 'traefik', 'portainer', 'redis', 'postgres', 'pgvector', 'minio']
            
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
    
    def show_summary(self, success: bool) -> None:
        """Exibe resumo da execução"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if success:
            self.logger.info(f"Setup concluído com sucesso ({duration:.2f}s)")
            self.logger.info("Próximas etapas: Portainer, Traefik, aplicações")
        else:
            self.logger.error(f"Setup concluído com falhas ({duration:.2f}s)")
