#!/usr/bin/env python3
"""
Módulo de instalação e configuração do Docker
Baseado no SetupOrionOriginal.sh - linhas 3548-3620
"""

import subprocess
import os
from .base_setup import BaseSetup

class DockerSetup(BaseSetup):
    """Instalação e configuração do Docker"""
    
    def __init__(self, enable_swarm: bool = True):
        super().__init__("Instalação do Docker")
        self.enable_swarm = enable_swarm
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Verifica se já está instalado
        if self.is_docker_installed():
            self.logger.info("Docker já está instalado")
            return True
            
        return True
    
    def is_docker_installed(self) -> bool:
        """Verifica se o Docker está instalado"""
        try:
            result = subprocess.run(
                "docker --version",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"Docker encontrado: {version}")
                return True
        except Exception as e:
            self.logger.debug(f"Docker não encontrado: {e}")
        return False
    
    def get_server_ip(self) -> str:
        """Obtém o IP do servidor"""
        try:
            # Usa o mesmo método do script original
            result = subprocess.run(
                "hostname -I | tr ' ' '\\n' | grep -v '^127\\.0\\.0\\.1' | grep -v '^10\\.0\\.0\\.' | head -1",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                self.logger.info(f"IP do servidor: {ip}")
                return ip
        except Exception as e:
            self.logger.debug(f"Erro ao obter IP: {e}")
        
        # Fallback: tenta com curl
        try:
            result = subprocess.run(
                "curl -s ifconfig.me",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                self.logger.info(f"IP externo: {ip}")
                return ip
        except Exception as e:
            self.logger.debug(f"Erro ao obter IP externo: {e}")
        
        return ""
    
    def install_docker_via_script(self) -> bool:
        """Instala Docker usando o script oficial"""
        self.logger.info("Tentando instalação via get.docker.com")
        
        # Download e execução do script
        if not self.run_command(
            "curl -fsSL https://get.docker.com | bash",
            "download e instalação do Docker via script oficial",
            timeout=600  # 10 minutos
        ):
            return False
        
        # Habilita e inicia o serviço
        if not self.run_command("systemctl enable docker", "habilitação do serviço Docker"):
            return False
            
        if not self.run_command("systemctl start docker", "inicialização do serviço Docker"):
            return False
        
        return True
    
    def install_docker_manual(self) -> bool:
        """Instalação manual do Docker via repositório oficial"""
        self.logger.info("Tentando instalação manual do Docker")
        
        # Instala dependências
        dependencies = [
            "ca-certificates",
            "curl", 
            "gnupg",
            "lsb-release"
        ]
        
        for dep in dependencies:
            if not self.run_command(
                f"apt-get install -y {dep}",
                f"instalação de {dep}"
            ):
                self.logger.warning(f"Falha ao instalar {dep}, continuando...")
        
        # Cria diretório para chaves
        if not self.run_command(
            "install -m 0755 -d /etc/apt/keyrings",
            "criação do diretório de chaves"
        ):
            return False
        
        # Adiciona chave GPG do Docker
        if not self.run_command(
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | tee /etc/apt/keyrings/docker.asc > /dev/null",
            "adição da chave GPG do Docker"
        ):
            return False
        
        if not self.run_command(
            "chmod a+r /etc/apt/keyrings/docker.asc",
            "configuração de permissões da chave"
        ):
            return False
        
        # Adiciona repositório do Docker
        repo_command = '''echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu focal stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null'''
        
        if not self.run_command(
            repo_command,
            "adição do repositório Docker"
        ):
            return False
        
        # Atualiza lista de pacotes
        if not self.run_command(
            "apt-get update",
            "atualização da lista de pacotes"
        ):
            return False
        
        # Instala Docker
        docker_packages = [
            "docker-ce",
            "docker-ce-cli", 
            "containerd.io",
            "docker-buildx-plugin",
            "docker-compose-plugin"
        ]
        
        if not self.run_command(
            f"apt-get install -y {' '.join(docker_packages)}",
            "instalação dos pacotes Docker",
            timeout=600
        ):
            return False
        
        # Habilita e inicia serviços
        if not self.run_command("systemctl enable docker", "habilitação do Docker"):
            return False
            
        if not self.run_command("systemctl start docker", "inicialização do Docker"):
            return False
        
        return True
    
    def install_docker(self) -> bool:
        """Instala Docker tentando primeiro o script oficial, depois manual"""
        # Primeira tentativa: script oficial
        if self.install_docker_via_script():
            return True
        
        self.logger.warning("Instalação via script falhou, tentando instalação manual")
        
        # Segunda tentativa: instalação manual
        return self.install_docker_manual()
    
    def initialize_swarm(self, ip: str) -> bool:
        """Inicializa Docker Swarm"""
        if not self.enable_swarm:
            self.logger.info("Docker Swarm desabilitado")
            return True
        
        # Verifica se já está em modo swarm
        try:
            result = subprocess.run(
                "docker info --format '{{.Swarm.LocalNodeState}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            swarm_state = result.stdout.strip()
            if result.returncode == 0 and swarm_state == "active":
                self.logger.info("Docker Swarm já está ativo")
                return True
            else:
                self.logger.debug(f"Docker Swarm status: {swarm_state}")
        except Exception as e:
            self.logger.debug(f"Erro ao verificar status do Swarm: {e}")
        
        # Inicializa o swarm
        if ip:
            swarm_command = f"docker swarm init --advertise-addr {ip}"
        else:
            swarm_command = "docker swarm init"
        
        if not self.run_command(
            swarm_command,
            "inicialização do Docker Swarm"
        ):
            return False
        
        self.logger.info("Docker Swarm inicializado com sucesso")
        return True
    
    def verify_installation(self) -> bool:
        """Verifica se a instalação foi bem-sucedida"""
        # Verifica se Docker está funcionando
        if not self.run_command(
            "docker --version",
            "verificação da versão do Docker"
        ):
            return False
        
        # Testa execução de container
        if not self.run_command(
            "docker run --rm hello-world",
            "teste de execução de container",
            timeout=60
        ):
            self.logger.warning("Teste com hello-world falhou, mas Docker parece instalado")
        
        return True
    
    def run(self) -> bool:
        """Executa a instalação completa do Docker"""
        self.log_step_start("Instalação do Docker")
        
        if not self.validate_prerequisites():
            return False
        
        # Obtém IP do servidor
        server_ip = self.get_server_ip()
        if server_ip:
            self.logger.info(f"IP do servidor: {server_ip}")
        else:
            self.logger.warning("Não foi possível identificar IP do servidor")
        
        # Se já está instalado, pula instalação
        if self.is_docker_installed():
            self.logger.info("Docker já instalado, verificando configuração")
        else:
            # Instala Docker
            if not self.install_docker():
                return False
        
        # Verifica instalação
        if not self.verify_installation():
            return False
        
        # Inicializa Swarm se habilitado (sempre verifica)
        if not self.initialize_swarm(server_ip):
            self.logger.warning("Falha ao inicializar Docker Swarm, mas Docker foi instalado")
        
        duration = self.get_duration()
        self.logger.info(f"Instalação do Docker concluída ({duration:.2f}s)")
        self.log_step_complete("Instalação do Docker")
        
        return True

def main():
    """Função principal para teste do módulo"""
    import sys
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    enable_swarm = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-swarm":
        enable_swarm = False
    
    setup = DockerSetup(enable_swarm=enable_swarm)
    
    if setup.run():
        print("Docker instalado com sucesso")
    else:
        print("Falha na instalação do Docker")
        sys.exit(1)

if __name__ == "__main__":
    main()
