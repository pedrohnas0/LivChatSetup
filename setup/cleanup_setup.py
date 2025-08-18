#!/usr/bin/env python3
"""
Módulo de limpeza do ambiente Docker Swarm
Remove completamente stacks, volumes, redes e reinicializa o Swarm
"""

import subprocess
import os
import time
from .base_setup import BaseSetup

class CleanupSetup(BaseSetup):
    """Limpeza completa do ambiente Docker Swarm"""
    
    def __init__(self):
        super().__init__("Limpeza do Ambiente Docker")
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Verifica se Docker está instalado
        if not self.is_docker_running():
            self.logger.warning("Docker não está rodando")
            return False
            
        return True
    
    def is_docker_running(self) -> bool:
        """Verifica se Docker está rodando"""
        try:
            result = subprocess.run(
                "docker info",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.debug(f"Erro ao verificar Docker: {e}")
            return False
    
    def remove_stacks(self) -> bool:
        """Remove todas as stacks do Docker Swarm"""
        self.logger.info("Removendo stacks do Docker Swarm")
        
        try:
            # Lista todas as stacks
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stacks = result.stdout.strip().split('\n')
                for stack in stacks:
                    if stack.strip():
                        self.logger.info(f"Removendo stack: {stack}")
                        if not self.run_command(
                            f"docker stack rm {stack}",
                            f"remoção da stack {stack}"
                        ):
                            self.logger.warning(f"Falha ao remover stack {stack}")
                
                # Aguarda remoção completa com polling
                self.logger.info("Aguardando remoção completa das stacks")
                deadline = time.time() + 60
                while time.time() < deadline:
                    check = subprocess.run(
                        "docker stack ls --format '{{.Name}}'",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    remaining = [s for s in check.stdout.strip().split('\n') if s.strip()] if check.returncode == 0 else []
                    if not remaining:
                        break
                    time.sleep(3)
                # Fallback: remover serviços remanescentes, se houver
                svc = subprocess.run(
                    "docker service ls -q",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if svc.returncode == 0 and svc.stdout.strip():
                    ids = svc.stdout.strip().split('\n')
                    for sid in ids:
                        if sid:
                            self.run_command(f"docker service rm {sid}", "remoção de serviço remanescente")
            else:
                self.logger.info("Nenhuma stack encontrada")
                
        except Exception as e:
            self.logger.error(f"Erro ao listar stacks: {e}")
            return False
            
        return True
    
    def remove_volumes(self) -> bool:
        """Remove volumes do projeto (lista conhecida + varredura por prefixo)"""
        # Lista estática conhecida dos módulos do projeto
        static_vols = [
            # Core
            'vol_certificates', 'portainer_data', 'volume_swarm_shared',
            # DBs
            'redis_data', 'postgres_data', 'pgvector_data',
            # Evolution
            'evolution_instances',
            # Chatwoot
            'chatwoot_mailer', 'chatwoot_mailers', 'chatwoot_public', 'chatwoot_redis', 'chatwoot_storage',
            # Directus
            'directus_extensions', 'directus_uploads',
            # GOWA
            'gowa_gowa_data',
            # Grafana
            'grafana_grafana_data', 'grafana_prometheus_data',
            # Passbolt
            'passbolt_database', 'passbolt_gpg', 'passbolt_jwt'
        ]
        # Prefixos para varredura dinâmica
        prefixes = [
            'chatwoot_', 'directus_', 'grafana_', 'passbolt_', 'gowa_',
            'pgvector', 'postgres', 'redis', 'evolution', 'minio', 'livchatbridge'
        ]
        self.logger.info("Removendo volumes do projeto (estáticos + dinâmicos)")

        # Coleta todos os volumes existentes
        try:
            list_all = subprocess.run(
                "docker volume ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20
            )
            all_vols = set([v.strip() for v in list_all.stdout.split('\n') if v.strip()]) if list_all.returncode == 0 else set()
        except Exception as e:
            self.logger.warning(f"Falha ao listar volumes: {e}")
            all_vols = set()

        # Monta conjunto alvo
        targets = set(static_vols)
        for v in all_vols:
            if any(v.startswith(p) for p in prefixes):
                targets.add(v)

        # Remove um a um (idempotente)
        for volume in sorted(targets):
            try:
                if volume in all_vols:
                    self.logger.info(f"Removendo volume: {volume}")
                    if not self.run_command(
                        f"docker volume rm {volume}",
                        f"remoção do volume {volume}"
                    ):
                        self.logger.warning(f"Falha ao remover volume {volume}")
                else:
                    self.logger.debug(f"Volume {volume} não encontrado")
            except Exception as e:
                self.logger.error(f"Erro ao remover volume {volume}: {e}")

        return True
    
    def remove_networks(self) -> bool:
        """Remove redes não padrão (de projetos)"""
        self.logger.info("Removendo redes do projeto")
        default_networks = {"bridge", "host", "none", "docker_gwbridge", "ingress"}
        try:
            result = subprocess.run(
                "docker network ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20
            )
            if result.returncode == 0:
                networks = [n.strip() for n in result.stdout.split('\n') if n.strip()]
                for net in networks:
                    if net not in default_networks:
                        self.logger.info(f"Removendo rede: {net}")
                        if not self.run_command(
                            f"docker network rm {net}",
                            f"remoção da rede {net}"
                        ):
                            self.logger.warning(f"Falha ao remover rede {net}")
            else:
                self.logger.warning("Falha ao listar redes")
        except Exception as e:
            self.logger.error(f"Erro ao remover redes: {e}")
        return True
    
    def prune_docker_system(self) -> bool:
        """Limpa sistema Docker (containers, imagens, etc.)"""
        self.logger.info("Limpando sistema Docker")
        
        commands = [
            ("docker container prune -f", "limpeza de containers parados"),
            ("docker image prune -af", "limpeza de imagens não utilizadas (todas)"),
            ("docker network prune -f", "limpeza de redes não utilizadas"),
            ("docker volume prune -f", "limpeza de volumes não utilizados"),
            ("docker system prune -af --volumes", "limpeza geral do sistema (forçada)")
        ]
        
        for command, description in commands:
            if not self.run_command(command, description):
                self.logger.warning(f"Falha na {description}")
        
        return True
    
    def leave_swarm(self) -> bool:
        """Sai do Docker Swarm"""
        self.logger.info("Saindo do Docker Swarm")
        
        try:
            # Verifica se está em modo swarm
            result = subprocess.run(
                "docker info --format '{{.Swarm.LocalNodeState}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                swarm_state = result.stdout.strip()
                if swarm_state == "active":
                    self.logger.info("Docker Swarm ativo, saindo do cluster")
                    if not self.run_command(
                        "docker swarm leave --force",
                        "saída do Docker Swarm"
                    ):
                        return False
                else:
                    self.logger.info(f"Docker Swarm não está ativo (status: {swarm_state})")
            else:
                self.logger.warning("Não foi possível verificar status do Swarm")
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar/sair do Swarm: {e}")
            return False
            
        return True
    
    def remove_stack_files(self) -> bool:
        """Remove arquivos de stack temporários"""
        files_to_remove = [
            '/tmp/traefik-stack.yml',
            '/tmp/portainer-stack.yml',
            '/root/traefik.yaml',
            '/root/portainer.yaml'
        ]
        
        self.logger.info("Removendo arquivos de stack")
        
        for file_path in files_to_remove:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"Arquivo removido: {file_path}")
                else:
                    self.logger.debug(f"Arquivo não encontrado: {file_path}")
            except Exception as e:
                self.logger.warning(f"Erro ao remover {file_path}: {e}")
        
        return True
    
    def _get_confirmation(self) -> bool:
        """Solicita confirmação do usuário para limpeza"""
        print("\n=== ATENÇÃO: LIMPEZA COMPLETA DO AMBIENTE ===")
        print("Esta operação irá remover:")
        print("- TODAS as stacks do Docker Swarm")
        print("- TODOS os volumes do projeto")
        print("- TODAS as redes do projeto")
        print("- Sairá do Docker Swarm")
        print("- Limpará containers, imagens e volumes não utilizados")
        print("\nEsta ação É IRREVERSÍVEL!")
        
        while True:
            confirm = input("\nDigite 'CONFIRMO' para prosseguir ou 'cancelar' para abortar: ").strip()
            if confirm == 'CONFIRMO':
                return True
            elif confirm.lower() in ['cancelar', 'cancel', 'n', 'no']:
                return False
            else:
                print("Resposta inválida. Digite 'CONFIRMO' ou 'cancelar'.")
    
    def run(self) -> bool:
        """Executa a limpeza completa"""
        self.log_step_start("Limpeza do Ambiente Docker")
        
        # Solicita confirmação do usuário
        if not self._get_confirmation():
            self.logger.info("Limpeza cancelada pelo usuário")
            return False
        
        if not self.validate_prerequisites():
            return False
        
        # Sequência de limpeza
        steps = [
            ("Remoção de stacks", self.remove_stacks),
            ("Remoção de volumes", self.remove_volumes),
            ("Remoção de redes", self.remove_networks),
            ("Saída do Swarm", self.leave_swarm),
            ("Limpeza do sistema", self.prune_docker_system),
            ("Remoção de arquivos", self.remove_stack_files)
        ]
        
        for step_name, step_func in steps:
            self.logger.info(f"Etapa: {step_name}")
            if not step_func():
                self.logger.error(f"Falha na etapa: {step_name}")
                # Continua mesmo com falhas para tentar limpar o máximo possível
        
        duration = self.get_duration()
        self.logger.info(f"Limpeza concluída ({duration:.2f}s)")
        self.log_step_complete("Limpeza do Ambiente Docker")
        
        return True

def main():
    """Função principal para teste do módulo"""
    import sys
    sys.path.append('/root/CascadeProjects')
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    cleanup = CleanupSetup()
    
    if cleanup.run():
        print("Limpeza concluída com sucesso")
    else:
        print("Limpeza concluída com algumas falhas")
        sys.exit(1)

if __name__ == "__main__":
    main()
