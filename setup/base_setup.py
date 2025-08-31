#!/usr/bin/env python3
"""
Classe base para todos os módulos de setup
"""

import subprocess
import sys
import os
import logging
import unicodedata
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseSetup(ABC):
    """Classe base abstrata para todos os módulos de setup"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
        self.start_time = datetime.now()
        
    @abstractmethod
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos antes da execução"""
        pass
    
    @abstractmethod
    def run(self) -> bool:
        """Executa o setup principal"""
        pass
    
    def cleanup(self) -> bool:
        """Limpeza após execução (opcional)"""
        return True
    
    def check_root(self) -> bool:
        """Verifica se está executando como root"""
        if os.geteuid() != 0:
            self.logger.error("Script deve ser executado como root")
            self.logger.error("Execute: sudo python3 <script>")
            return False
        return True
    
    def run_command(self, command: str, description: str, critical: bool = True, timeout: int = 300) -> bool:
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
                timeout=timeout
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self.logger.info(f"Sucesso {description} ({duration:.2f}s)")
                
                # Log da saída se houver
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.logger.debug(line)
                
                return True
            else:
                self.logger.error(f"Falha {description} (código: {result.returncode}, {duration:.2f}s)")
                
                # Log dos erros
                if result.stderr.strip():
                    for line in result.stderr.strip().split('\n'):
                        self.logger.error(line)
                
                # Log da saída padrão se houver
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.logger.debug(line)
                
                if critical:
                    self.logger.critical(f"Comando crítico falhou: {description}")
                
                return False
                
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Timeout {description} ({duration:.2f}s)")
            if critical:
                self.logger.critical(f"Timeout em comando crítico: {description}")
            return False
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Exceção {description} ({duration:.2f}s): {type(e).__name__}: {str(e)}")
            if critical:
                self.logger.critical(f"Exceção em comando crítico: {description}")
            return False
    
    def check_package_installed(self, package: str) -> tuple[bool, str]:
        """Verifica se um pacote está instalado e retorna sua versão"""
        try:
            result = subprocess.run(
                f"dpkg -l | grep '^ii' | grep '{package}' | awk '{{print $3}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip().split('\n')[0]
                return True, version
            else:
                return False, ""
                
        except Exception as e:
            self.logger.debug(f"Erro ao verificar pacote {package}: {e}")
            return False, ""
    
    def get_system_info(self) -> Dict[str, str]:
        """Coleta informações básicas do sistema"""
        info = {}
        
        try:
            # Distribuição
            result = subprocess.run("lsb_release -d | cut -f2", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['distribuicao'] = result.stdout.strip()
        except:
            info['distribuicao'] = 'Desconhecida'
        
        try:
            # Kernel
            result = subprocess.run("uname -r", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['kernel'] = result.stdout.strip()
        except:
            info['kernel'] = 'Desconhecido'
        
        try:
            # Data/Hora
            result = subprocess.run("date", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['data_hora'] = result.stdout.strip()
        except:
            info['data_hora'] = 'Desconhecida'
        
        return info
    
    def log_step_start(self, step: str):
        """Log do início de uma etapa"""
        self.logger.info(f"Etapa: {step}")
    
    def log_step_complete(self, step: str):
        """Log da conclusão de uma etapa"""
        self.logger.info(f"Concluído: {step}")
    
    def get_duration(self) -> float:
        """Retorna a duração total da execução"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_display_width(self, text: str) -> int:
        """Calcula largura visual real considerando emojis e caracteres especiais"""
        width = 0
        for char in text:
            # East Asian characters (incluindo emojis) são tipicamente 2 unidades de largura
            if unicodedata.east_asian_width(char) in ('F', 'W'):
                width += 2
            # Variation selectors são de largura zero
            elif unicodedata.combining(char) or ord(char) == 65039:  # variation selector-16
                width += 0
            # Caracteres normais
            else:
                width += 1
        return width
    
    def center_text_with_display_width(self, text: str, total_width: int, padding_adjustment: int = 0) -> str:
        """Centraliza texto considerando largura de caracteres"""
        # Use len() instead of display_width for better terminal compatibility  
        text_length = len(text)
        if text_length >= total_width:
            return text
        padding = ((total_width - text_length) // 2) + padding_adjustment
        return ' ' * padding + text + ' ' * (total_width - text_length - padding)
