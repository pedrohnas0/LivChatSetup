#!/usr/bin/env python3
"""
Configurações globais do sistema de setup
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Configurações de logging
LOG_LEVEL = logging.DEBUG
LOG_FILE = '/var/log/setup_inicial.log'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Configurações de timeout
COMMAND_TIMEOUT = 300  # 5 minutos
NETWORK_TIMEOUT = 30   # 30 segundos

# Intervalos globais de polling/log para espera de serviços
# Checagem rápida e silenciosa (ex.: 300ms) e emissão de logs a cada 5s
POLL_INTERVAL_FAST_SECONDS = 0.3   # 300ms
LOG_STATUS_INTERVAL_SECONDS = 5    # logs de progresso a cada 5 segundos
WAIT_TIMEOUT_SECONDS_DEFAULT = 300 # timeout padrão para aguardar serviços

# Configurações do sistema
TIMEZONE = 'America/Sao_Paulo'
BASIC_PACKAGES = [
    'apt-utils',
    'apparmor-utils',
    'curl',
    'wget',
    'ca-certificates',
    'gnupg',
    'lsb-release'
]

def setup_logging(console_level='INFO'):
    """Configura o sistema de logging global
    
    Args:
        console_level: Nível de log para console ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
                      O arquivo sempre recebe DEBUG para auditoria completa
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Logger principal sempre DEBUG
    
    # Converte string para nível do logging
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    console_log_level = level_map.get(console_level.upper(), logging.INFO)
    
    # Remove handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter técnico
    class TechnicalFormatter(logging.Formatter):
        def format(self, record):
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            level = record.levelname.center(8)
            message = record.getMessage()
            return f"{timestamp} | {level} | {message}"
    
    # Formatter colorido para console
    class ColoredTechnicalFormatter(TechnicalFormatter):
        COLORS = {
            'DEBUG': '\033[36m',
            'INFO': '\033[32m',
            'WARNING': '\033[33m',
            'ERROR': '\033[31m',
            'CRITICAL': '\033[31;1m',
            'RESET': '\033[0m'
        }
        
        def format(self, record):
            formatted = super().format(record)
            color = self.COLORS.get(record.levelname, '')
            return f"{color}{formatted}{self.COLORS['RESET']}"
    
    # Handler para console (nível configurável)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(ColoredTechnicalFormatter())
    logger.addHandler(console_handler)
    
    # Handler para arquivo com rotação (sempre DEBUG para auditoria)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=LOG_MAX_SIZE, 
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)  # Arquivo sempre recebe tudo
    file_handler.setFormatter(TechnicalFormatter())
    logger.addHandler(file_handler)
    
    return logger
