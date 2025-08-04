#!/usr/bin/env python3
"""
Setup Inicial Simplificado
Baseado no SetupOrionOriginal.sh - Preparativos iniciais do sistema
"""

import subprocess
import sys
import os
import logging
from datetime import datetime

# Remove duplicações - usa config.py

class SystemSetup:
    def __init__(self):
        # Usa o logging já configurado em config.py
        import sys
        sys.path.append('/root/CascadeProjects')
        from config import setup_logging
        self.logger = setup_logging()
        
    def check_root(self):
        """Verifica se está executando como root"""
        if os.geteuid() != 0:
            self.logger.error("Script deve ser executado como root")
            self.logger.error("Execute: sudo python3 setup_inicial.py")
            sys.exit(1)
        self.logger.info("Verificação de privilégios: OK")
    
    def run_command(self, command, description, critical=True):
        """Executa comando com logging detalhado"""
        start_time = datetime.now()
        self.logger.info(f"Executando {description}")
        self.logger.debug(f"Comando: {command}")
        self.logger.debug(f"Diretório: {os.getcwd()}")
        self.logger.debug(f"Usuário: {os.getenv('USER', 'unknown')}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self.logger.info(f"Sucesso {description} ({duration:.2f}s)")
                
                # Sempre mostrar toda a saída
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.logger.debug(line)
                
                return True
            else:
                self.logger.error(f"Falha {description} (código: {result.returncode}, {duration:.2f}s)")
                
                # Mostrar todos os erros
                if result.stderr.strip():
                    for line in result.stderr.strip().split('\n'):
                        self.logger.error(line)
                
                # Mostrar saída padrão se houver
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.logger.debug(line)
                
                return False
                
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Timeout {description} ({duration:.2f}s)")
            return False
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Exceção {description} ({duration:.2f}s): {type(e).__name__}: {str(e)}")
            return False
    
    def update_system(self):
        """Atualiza o sistema"""
        self.logger.info("Iniciando atualização do sistema")
        
        # Verificar espaço em disco
        disk_result = subprocess.run("df -h / | tail -1 | awk '{print $4}'", shell=True, capture_output=True, text=True)
        if disk_result.returncode == 0:
            self.logger.debug(f"Espaço disponível: {disk_result.stdout.strip()}")
        
        # Update da lista de pacotes
        if not self.run_command("apt-get update", "atualização da lista de pacotes"):
            return False
            
        # Verificar pacotes atualizáveis
        upgradable = subprocess.run("apt list --upgradable 2>/dev/null | wc -l", shell=True, capture_output=True, text=True)
        if upgradable.returncode == 0:
            count = int(upgradable.stdout.strip()) - 1
            self.logger.info(f"Pacotes atualizáveis: {count}")
        
        # Upgrade do sistema
        if not self.run_command("apt upgrade -y", "upgrade dos pacotes"):
            return False
            
        self.logger.info("Sistema atualizado")
        return True
    
    def configure_timezone(self):
        """Configura timezone para São Paulo"""
        self.logger.info("Configurando timezone")
        
        # Verificar timezone atual
        current_tz = subprocess.run("timedatectl show --property=Timezone --value", shell=True, capture_output=True, text=True)
        if current_tz.returncode == 0:
            current = current_tz.stdout.strip()
            self.logger.debug(f"Timezone atual: {current}")
            
            if current == "America/Sao_Paulo":
                self.logger.info("Timezone já configurado")
                return True
        
        # Configurar novo timezone
        if self.run_command("timedatectl set-timezone America/Sao_Paulo", "configuração do timezone"):
            # Verificar aplicação
            verify_result = subprocess.run("timedatectl show --property=Timezone --value", shell=True, capture_output=True, text=True)
            if verify_result.returncode == 0:
                new_tz = verify_result.stdout.strip()
                if new_tz == "America/Sao_Paulo":
                    self.logger.info(f"Timezone alterado: {current} -> {new_tz}")
                    
                    # Horário atual
                    time_result = subprocess.run("date", shell=True, capture_output=True, text=True)
                    if time_result.returncode == 0:
                        self.logger.info(f"Horário: {time_result.stdout.strip()}")
                    
                    return True
                else:
                    self.logger.error(f"Timezone incorreto. Esperado: America/Sao_Paulo, Atual: {new_tz}")
            else:
                self.logger.error("Não foi possível verificar timezone")
        
        return False
    
    def install_basic_packages(self):
        """Instala pacotes básicos necessários"""
        self.logger.info("Instalando pacotes básicos")
        
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
            check_cmd = f"dpkg -l | grep -q '^ii  {package} '"
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if check_result.returncode == 0:
                # Obter versão
                version_cmd = f"dpkg -l {package} | tail -1 | awk '{{print $3}}'"
                version_result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
                    self.logger.info(f"Já instalado: {package} v{version}")
                success_count += 1
                continue
            
            # Instalar pacote
            if self.run_command(f"apt-get install -y {package}", f"instalação {package}"):
                success_count += 1
                # Verificar versão instalada
                version_cmd = f"dpkg -l {package} | tail -1 | awk '{{print $3}}'"
                version_result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
                    self.logger.info(f"Instalado: {package} v{version}")
            else:
                self.logger.error(f"Falha: {package}")
        
        # Atualizar cache
        if self.run_command("apt-get update", "atualização do cache"):
            self.logger.info(f"Pacotes instalados: {success_count}/{total_packages}")
        else:
            self.logger.warning("Falha ao atualizar cache")
            
        return success_count == total_packages
    
    def run_basic_setup(self):
        """Executa setup básico do sistema"""
        start_time = datetime.now()
        self.logger.info("Iniciando setup básico")
        self.logger.debug(f"Timestamp: {start_time.isoformat()}")
        self.logger.debug(f"Usuário: {os.getenv('USER', 'unknown')}")
        self.logger.debug(f"Hostname: {os.uname().nodename}")
        
        steps = [
            ("Verificação de privilégios", self.check_root),
            ("Atualização do sistema", self.update_system),
            ("Configuração de timezone", self.configure_timezone),
            ("Instalação de pacotes básicos", self.install_basic_packages)
        ]
        
        failed_steps = []
        
        for step_name, step_func in steps:
            self.logger.info(f"Etapa: {step_name}")
            try:
                if step_name == "Verificação de privilégios":
                    step_func()
                    continue
                    
                if not step_func():
                    failed_steps.append(step_name)
                    self.logger.error(f"Falha: {step_name}")
                else:
                    self.logger.info(f"Concluído: {step_name}")
                    
            except Exception as e:
                failed_steps.append(step_name)
                self.logger.error(f"Exceção {step_name}: {str(e)}")
        
        # Relatório final
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if failed_steps:
            self.logger.warning(f"Setup concluído com falhas ({len(failed_steps)}): {', '.join(failed_steps)}")
        else:
            self.logger.info(f"Setup básico concluído ({duration:.2f}s)")
        
        # Estado do sistema
        version_checks = [
            ("lsb_release -d", "Distribuição"),
            ("uname -r", "Kernel"),
            ("date '+%Y-%m-%d %H:%M:%S %Z'", "Data/Hora")
        ]
        
        for cmd, desc in version_checks:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                info = result.stdout.strip().replace('Description:\t', '')
                self.logger.debug(f"{desc}: {info}")
        
        # Próximas etapas
        self.logger.info("Próximas etapas: hostname, Docker, rede")
        
        return len(failed_steps) == 0

def main():
    setup = SystemSetup()
    
    try:
        success = setup.run_basic_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        setup.logger.warning("Setup interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        setup.logger.critical(f"Erro crítico: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
