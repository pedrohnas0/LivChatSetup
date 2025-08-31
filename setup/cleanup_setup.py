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
                        # Comando mais robusto para remoção de stack
                        success = self.run_command(
                            f"docker stack rm {stack} 2>/dev/null || true",
                            f"remoção da stack {stack}"
                        )
                        if not success:
                            # Tenta forçar remoção de serviços individuais
                            self.logger.warning(f"Falha ao remover stack {stack}, tentando remoção forçada")
                            self._force_remove_stack_services(stack)
                
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
        """Remove volumes do projeto de forma ultra-robusta"""
        self.logger.info("Removendo volumes do projeto (ultra-robusta)")

        # ETAPA 1: Para todos os containers ativos que podem estar usando volumes
        self._force_stop_all_containers()

        # ETAPA 2: Coleta todos os volumes existentes
        try:
            list_all = subprocess.run(
                "docker volume ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20
            )
            all_volumes = [v.strip() for v in list_all.stdout.split('\n') if v.strip()] if list_all.returncode == 0 else []
        except Exception as e:
            self.logger.warning(f"Falha ao listar volumes: {e}")
            all_volumes = []

        if not all_volumes:
            self.logger.info("Nenhum volume encontrado para remover")
            return True

        # ETAPA 3: Identifica volumes para remoção (mais abrangente)
        volumes_to_remove = set()
        
        # Padrões expandidos para capturar TODOS os volumes possíveis do projeto
        patterns = [
            'buildx_', 'openwebui_', 'vol_', 'portainer', 'traefik',
            'chatwoot_', 'directus_', 'grafana_', 'passbolt_', 'gowa_',
            'pgvector', 'postgres', 'redis', 'evolution', 'minio', 'livchatbridge',
            'n8n_', 'docker_', 'swarm_', 'livchat'
        ]
        
        # Se contém qualquer padrão conhecido, será removido
        for volume in all_volumes:
            volume_lower = volume.lower()
            for pattern in patterns:
                if pattern in volume_lower:
                    volumes_to_remove.add(volume)
                    break
        
        # Exclui volumes críticos do sistema
        system_volumes = {'docker_gwbridge', 'ingress', 'docker_default'}
        volumes_to_remove = volumes_to_remove - system_volumes
        
        if not volumes_to_remove:
            self.logger.info("Nenhum volume do projeto encontrado para remover")
            return True
        
        self.logger.info(f"Encontrados {len(volumes_to_remove)} volumes para remoção")
        
        # ETAPA 4: Remoção ultra-robusta com múltiplas tentativas
        removed_count = 0
        failed_volumes = []
        
        for volume in sorted(volumes_to_remove):
            if self._remove_volume_ultra_robust(volume):
                removed_count += 1
            else:
                failed_volumes.append(volume)
        
        self.logger.info(f"Volumes removidos: {removed_count}/{len(volumes_to_remove)}")
        if failed_volumes:
            self.logger.warning(f"Volumes que falharam na remoção: {', '.join(failed_volumes)}")
        
        return len(failed_volumes) == 0
    
    def _force_stop_all_containers(self):
        """Para e remove TODOS os containers para liberar volumes"""
        self.logger.info("Parando todos os containers para liberar volumes")
        
        try:
            # Lista todos os containers (running e stopped)
            result = subprocess.run(
                "docker ps -aq",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_ids = [cid.strip() for cid in result.stdout.split('\n') if cid.strip()]
                
                if container_ids:
                    self.logger.info(f"Encontrados {len(container_ids)} containers para parar")
                    
                    # Para todos os containers de forma forçada
                    for container_id in container_ids:
                        self.run_command(
                            f"docker stop {container_id} --time 5 2>/dev/null || true",
                            f"parada forçada do container {container_id[:12]}",
                            critical=False
                        )
                    
                    # Remove todos os containers
                    self.run_command(
                        f"docker rm -f {' '.join(container_ids)} 2>/dev/null || true",
                        "remoção forçada de todos os containers",
                        critical=False
                    )
                    
                    # Aguarda um pouco para garantir que volumes sejam liberados
                    time.sleep(3)
                else:
                    self.logger.info("Nenhum container encontrado")
            else:
                self.logger.info("Nenhum container encontrado")
                
        except Exception as e:
            self.logger.warning(f"Erro ao parar containers: {e}")
    
    def _remove_volume_ultra_robust(self, volume: str) -> bool:
        """Remove um volume com múltiplas estratégias"""
        self.logger.info(f"Removendo volume: {volume}")
        
        # Estratégia 1: Remoção normal
        if self.run_command(f"docker volume rm {volume}", f"remoção do volume {volume}", critical=False):
            return True
        
        # Estratégia 2: Identifica e para containers usando este volume
        self._stop_containers_using_volume(volume)
        time.sleep(2)
        
        if self.run_command(f"docker volume rm {volume}", f"remoção do volume {volume} (após parar containers)", critical=False):
            return True
        
        # Estratégia 3: Remoção forçada
        if self.run_command(f"docker volume rm {volume} --force", f"remoção forçada do volume {volume}", critical=False):
            return True
        
        # Estratégia 4: Prune primeiro, depois tenta novamente
        self.run_command("docker system prune -f --volumes", "prune antes da remoção", critical=False)
        time.sleep(1)
        
        if self.run_command(f"docker volume rm {volume} --force 2>/dev/null || true", f"remoção final do volume {volume}", critical=False):
            return True
        
        self.logger.error(f"Falha definitiva ao remover volume {volume}")
        return False
    
    def _stop_containers_using_volume(self, volume: str):
        """Para containers que estão usando um volume específico"""
        try:
            # Busca containers que usam este volume
            result = subprocess.run(
                f"docker ps -q --filter volume={volume}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_ids = [cid.strip() for cid in result.stdout.split('\n') if cid.strip()]
                
                for container_id in container_ids:
                    self.logger.info(f"Parando container {container_id[:12]} que usa volume {volume}")
                    self.run_command(
                        f"docker stop {container_id} --time 3 2>/dev/null && docker rm {container_id} 2>/dev/null || true",
                        f"parada do container {container_id[:12]}",
                        critical=False
                    )
        except Exception as e:
            self.logger.debug(f"Erro ao parar containers usando volume {volume}: {e}")
    
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
                        # Comando mais robusto para remoção de rede
                        success = self.run_command(
                            f"docker network rm {net} 2>/dev/null || true",
                            f"remoção da rede {net}"
                        )
                        if not success:
                            self.logger.warning(f"Falha ao remover rede {net} (pode estar em uso)")
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
        
        # Limpeza adicional específica para volumes orphaned
        self._final_volume_cleanup()
        
        return True
    
    def _final_volume_cleanup(self) -> bool:
        """Limpeza final ultra-agressiva de volumes restantes"""
        self.logger.info("Executando limpeza final ultra-agressiva de volumes")
        
        # Para qualquer container que possa ter iniciado
        self._force_stop_all_containers()
        
        try:
            # Lista volumes restantes
            result = subprocess.run(
                "docker volume ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                remaining_volumes = [v.strip() for v in result.stdout.split('\n') if v.strip()]
                
                # Padrões expandidos para capturar QUALQUER volume suspeito
                project_patterns = [
                    'buildx_', 'openwebui_', 'vol_', 'portainer', 'traefik', 'chatwoot', 
                    'directus', 'grafana', 'postgres', 'redis', 'minio', 'n8n',
                    'evolution', 'gowa', 'passbolt', 'livchatbridge'
                ]
                
                volumes_to_force_remove = []
                
                for volume in remaining_volumes:
                    volume_lower = volume.lower()
                    # Se contém QUALQUER padrão conhecido, será removido na força
                    for pattern in project_patterns:
                        if pattern in volume_lower:
                            volumes_to_force_remove.append(volume)
                            break
                
                if volumes_to_force_remove:
                    self.logger.info(f"Removendo {len(volumes_to_force_remove)} volumes restantes do projeto")
                    
                    # Múltiplas tentativas com estratégias diferentes
                    for volume in volumes_to_force_remove:
                        self.logger.info(f"Limpeza final: removendo {volume}")
                        
                        # Tentativa 1: Remoção direta forçada
                        if self.run_command(f"docker volume rm {volume} --force", f"remoção ultra-forçada de {volume}", critical=False):
                            continue
                            
                        # Tentativa 2: Para Docker, remove, reinicia Docker
                        self.logger.warning(f"Volume {volume} resistente, usando estratégia extrema")
                        self.run_command("systemctl stop docker", "parada do Docker daemon", critical=False)
                        time.sleep(2)
                        self.run_command("systemctl start docker", "reinício do Docker daemon", critical=False)
                        time.sleep(3)
                        
                        # Tentativa 3: Após reiniciar Docker
                        self.run_command(f"docker volume rm {volume} --force 2>/dev/null || true", f"remoção pós-restart de {volume}", critical=False)
                        
                        # Tentativa 4: Remove diretamente do filesystem (última opção)
                        volume_path = f"/var/lib/docker/volumes/{volume}"
                        if os.path.exists(volume_path):
                            self.run_command(f"rm -rf {volume_path}", f"remoção filesystem de {volume}", critical=False)
                else:
                    self.logger.info("Nenhum volume do projeto restante encontrado")
                    
                # Limpeza final completa
                self.run_command("docker system prune -af --volumes", "limpeza sistema completa final", critical=False)
            
            return True
        except Exception as e:
            self.logger.warning(f"Erro na limpeza final de volumes: {e}")
            return True
    
    def _force_remove_stack_services(self, stack_name: str) -> None:
        """Força remoção de serviços de uma stack específica"""
        try:
            # Lista serviços da stack
            result = subprocess.run(
                f"docker service ls --filter label=com.docker.stack.namespace={stack_name} --format '{{{{.ID}}}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and result.stdout.strip():
                service_ids = result.stdout.strip().split('\n')
                for service_id in service_ids:
                    if service_id.strip():
                        self.run_command(
                            f"docker service rm {service_id.strip()} 2>/dev/null || true",
                            f"remoção forçada do serviço {service_id.strip()}"
                        )
        except Exception as e:
            self.logger.debug(f"Erro na remoção forçada de serviços da stack {stack_name}: {e}")
    
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
        # Cores ANSI definidas como variáveis
        cinza = "\033[90m"
        vermelho = "\033[91m"  
        bege = "\033[93m"
        laranja = "\033[38;5;173m"
        verde = "\033[32m"
        branco = "\033[97m"
        reset = "\033[0m"
        
        print("")
        
        # Caixa do título
        print(f"{cinza}╭─────────────────────────────────────────────────────────────────────────────────────────────────────╮{reset}")
        print(f"{cinza}│{reset}                                                                                                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja} ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██╗   ██╗██████╗ {reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja}██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║██║   ██║██╔══██╗{reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja}██║     ██║     █████╗  ███████║██╔██╗ ██║██║   ██║██████╔╝{reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja}██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║██║   ██║██╔═══╝ {reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja}╚██████╗███████╗███████╗██║  ██║██║ ╚████║╚██████╔╝██║     {reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                     {laranja} ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     {reset}                     {cinza}│{reset}")
        print(f"{cinza}│{reset}                                                                                                     {cinza}│{reset}")
        print(f"{cinza}╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯{reset}")
        print("")
        
        # Detalhes da operação
        print(f"{vermelho}⚠️  ATENÇÃO: Esta operação é IRREVERSÍVEL!{reset}")
        print("")
        print(f"{bege}Esta limpeza irá:{reset}")
        print(f"  {vermelho}•{reset} Remover TODAS as stacks do Docker Swarm")
        print(f"  {vermelho}•{reset} Remover TODOS os volumes do projeto")
        print(f"  {vermelho}•{reset} Remover TODAS as redes personalizadas")
        print(f"  {vermelho}•{reset} Sair do Docker Swarm")
        print(f"  {vermelho}•{reset} Limpar containers, imagens e volumes não utilizados")
        print("")
        
        while True:
            confirm = input(f"Digite '{verde}CONFIRMO{reset}' para prosseguir ou '{vermelho}cancelar{reset}' para abortar: ").strip()
            if confirm == 'CONFIRMO':
                return True
            elif confirm.lower() in ['cancelar', 'cancel', 'n', 'no']:
                return False
            else:
                print(f"{vermelho}Resposta inválida.{reset} Digite '{verde}CONFIRMO{reset}' ou '{vermelho}cancelar{reset}'.")
    
    def run(self) -> bool:
        """Executa a limpeza completa"""
        self.log_step_start("Limpeza do Ambiente Docker")
        
        # Solicita confirmação do usuário
        if not self._get_confirmation():
            self.logger.info("Limpeza cancelada pelo usuário")
            return False
        
        if not self.validate_prerequisites():
            return False
        
        # Sequência de limpeza mais robusta
        steps = [
            ("Remoção de stacks", self.remove_stacks),
            ("Pausa para finalização", lambda: time.sleep(5) or True),  # Aguarda containers pararem
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
