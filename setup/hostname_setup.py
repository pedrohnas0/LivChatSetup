#!/usr/bin/env python3
"""
Módulo de configuração de hostname
Baseado no SetupOrionOriginal.sh - linhas 3521-3532
"""

import subprocess
import os
from datetime import datetime
from .base_setup import BaseSetup

class HostnameSetup(BaseSetup):
    """Configuração de hostname do servidor"""
    
    def __init__(self, hostname: str = None):
        super().__init__("Configuração de Hostname")
        self.hostname = hostname
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos"""
        if not self.check_root():
            return False
            
        # Solicita hostname interativamente se não fornecido
        if not self.hostname:
            self.hostname = self._get_hostname_input()
            if not self.hostname:
                self.logger.error("Hostname é obrigatório")
                return False
            
        # Valida formato do hostname
        if not self._validate_hostname_format(self.hostname):
            self.logger.error(f"Formato de hostname inválido: {self.hostname}")
            return False
            
        return True
    
    def _get_hostname_input(self) -> str:
        """Solicita hostname do usuário interativamente"""
        print("\n=== Configuração de Hostname ===")
        while True:
            hostname = input("Digite o hostname do servidor: ").strip()
            if hostname:
                if self._validate_hostname_format(hostname):
                    return hostname
                else:
                    print("Formato de hostname inválido. Use apenas letras, números e hífens.")
            else:
                print("Hostname é obrigatório!")
    
    def _validate_hostname_format(self, hostname: str) -> bool:
        """Valida o formato do hostname"""
        import re
        # RFC 1123 hostname validation
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        return re.match(pattern, hostname) is not None
    
    def get_current_hostname(self) -> str:
        """Obtém o hostname atual"""
        try:
            result = subprocess.run(
                "hostname",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Erro ao obter hostname atual: {e}")
        return ""
    
    def set_hostname(self) -> bool:
        """Define o hostname do sistema"""
        current_hostname = self.get_current_hostname()
        
        if current_hostname == self.hostname:
            self.logger.info(f"Hostname já configurado: {self.hostname}")
            return True
            
        self.logger.info(f"Alterando hostname de '{current_hostname}' para '{self.hostname}'")
        
        # Define o hostname usando hostnamectl
        if not self.run_command(
            f"hostnamectl set-hostname {self.hostname}",
            "configuração do hostname"
        ):
            return False
            
        # Verifica se foi aplicado
        new_hostname = self.get_current_hostname()
        if new_hostname == self.hostname:
            self.logger.info(f"Hostname configurado com sucesso: {self.hostname}")
            return True
        else:
            self.logger.error(f"Falha na configuração do hostname. Atual: {new_hostname}")
            return False
    
    def update_hosts_file(self) -> bool:
        """Atualiza o arquivo /etc/hosts com o novo hostname"""
        hosts_file = "/etc/hosts"
        
        try:
            # Lê o arquivo atual
            with open(hosts_file, 'r') as f:
                content = f.read()
            
            # Backup do arquivo original
            backup_file = f"{hosts_file}.backup.{int(datetime.now().timestamp())}"
            with open(backup_file, 'w') as f:
                f.write(content)
            self.logger.debug(f"Backup criado: {backup_file}")
            
            # Atualiza a linha do localhost
            import re
            # Padrão para encontrar a linha 127.0.0.1
            pattern = r'^127\.0\.0\.1\s+.*$'
            new_line = f"127.0.0.1 {self.hostname} localhost"
            
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
    
    def verify_configuration(self) -> bool:
        """Verifica se a configuração foi aplicada corretamente"""
        # Verifica hostname
        current_hostname = self.get_current_hostname()
        if current_hostname != self.hostname:
            self.logger.error(f"Hostname não configurado corretamente. Esperado: {self.hostname}, Atual: {current_hostname}")
            return False
        
        # Verifica /etc/hosts
        try:
            with open("/etc/hosts", 'r') as f:
                content = f.read()
            
            if self.hostname in content:
                self.logger.debug("Hostname encontrado em /etc/hosts")
                return True
            else:
                self.logger.warning("Hostname não encontrado em /etc/hosts")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar /etc/hosts: {e}")
            return False
    
    def run(self) -> bool:
        """Executa a configuração completa do hostname"""
        self.log_step_start("Configuração de hostname")
        
        if not self.validate_prerequisites():
            return False
        
        # Define o hostname
        if not self.set_hostname():
            return False
        
        # Atualiza /etc/hosts
        if not self.update_hosts_file():
            self.logger.warning("Falha ao atualizar /etc/hosts, mas hostname foi configurado")
        
        # Verifica configuração
        if not self.verify_configuration():
            self.logger.warning("Verificação da configuração falhou")
        
        duration = self.get_duration()
        self.logger.info(f"Configuração de hostname concluída ({duration:.2f}s)")
        self.log_step_complete("Configuração de hostname")
        
        return True

def main():
    """Função principal para teste do módulo"""
    import sys
    from config import setup_logging
    
    # Configura logging
    setup_logging()
    
    if len(sys.argv) < 2:
        print("Uso: python3 hostname_setup.py <hostname>")
        sys.exit(1)
    
    hostname = sys.argv[1]
    setup = HostnameSetup(hostname)
    
    if setup.run():
        print(f"Hostname configurado com sucesso: {hostname}")
    else:
        print("Falha na configuração do hostname")
        sys.exit(1)

if __name__ == "__main__":
    main()
