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
                
                # Aguarda remoção completa
                self.logger.info("Aguardando remoção completa das stacks")
                time.sleep(10)
            else:
                self.logger.info("Nenhuma stack encontrada")
                
        except Exception as e:
            self.logger.error(f"Erro ao listar stacks: {e}")
            return False
            
        return True
    
    def remove_volumes(self) -> bool:
        """Remove volumes específicos do projeto"""
        volumes_to_remove = [
            'vol_certificates',
            'portainer_data',
            'volume_swarm_shared'
        ]
        
        self.logger.info("Removendo volumes do projeto")
        
        for volume in volumes_to_remove:
            try:
                # Verifica se o volume existe
                result = subprocess.run(
                    f"docker volume ls --filter name={volume} --format '{{{{.Name}}}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and volume in result.stdout:
                    self.logger.info(f"Removendo volume: {volume}")
                    if not self.run_command(
                        f"docker volume rm {volume}",
                        f"remoção do volume {volume}"
                    ):
                        self.logger.warning(f"Falha ao remover volume {volume}")
                else:
                    self.logger.debug(f"Volume {volume} não encontrado")
                    
            except Exception as e:
                self.logger.error(f"Erro ao verificar volume {volume}: {e}")
        
        return True
    
    def remove_networks(self) -> bool:
        """Remove redes específicas do projeto"""
        networks_to_remove = [
            'orion_network',
            'volume_swarm_shared'
        ]
        
        self.logger.info("Removendo redes do projeto")
        
        for network in networks_to_remove:
            try:
                # Verifica se a rede existe
                result = subprocess.run(
                    f"docker network ls --filter name={network} --format '{{{{.Name}}}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and network in result.stdout:
                    self.logger.info(f"Removendo rede: {network}")
                    if not self.run_command(
                        f"docker network rm {network}",
                        f"remoção da rede {network}"
                    ):
                        self.logger.warning(f"Falha ao remover rede {network}")
                else:
                    self.logger.debug(f"Rede {network} não encontrada")
                    
            except Exception as e:
                self.logger.error(f"Erro ao verificar rede {network}: {e}")
        
        return True
    
    def prune_docker_system(self) -> bool:
        """Limpa sistema Docker (containers, imagens, etc.)"""
        self.logger.info("Limpando sistema Docker")
        
        commands = [
            ("docker container prune -f", "limpeza de containers parados"),
            ("docker image prune -f", "limpeza de imagens não utilizadas"),
            ("docker network prune -f", "limpeza de redes não utilizadas"),
            ("docker volume prune -f", "limpeza de volumes não utilizados"),
            ("docker system prune -f", "limpeza geral do sistema")
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
    
    def run(self) -> bool:
        """Executa a limpeza completa"""
        self.log_step_start("Limpeza do Ambiente Docker")
        
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
