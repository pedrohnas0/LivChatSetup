#!/usr/bin/env python3
"""
Gerenciador de Configurações Centralizado
Substitui os múltiplos arquivos dados_vps/* por um JSON único
"""

import json
import os
import logging
import secrets
import string
from typing import Dict, Any, Optional, List
from datetime import datetime

class ConfigManager:
    """Gerenciador centralizado de configurações do LivChatSetup"""
    
    def __init__(self, config_path: str = "/root/livchat-config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config_data = self._load_config()
        
        # Garantir estrutura básica
        self._ensure_structure()
    
    def _ensure_structure(self):
        """Garante que a estrutura básica do config existe"""
        default_structure = {
            "global": {
                "user_email": "",
                "default_subdomain": "",
                "cloudflare_auto_dns": False,
                "network_name": "",
                "hostname": "",
                "installation_date": datetime.now().isoformat(),
                "version": "2.0"
            },
            "cloudflare": {
                "api_token": "",
                "zone_id": "",
                "zone_name": "",
                "enabled": False
            },
            "credentials": {},
            "applications": {}
        }
        
        # Mescla com configuração existente
        for key, value in default_structure.items():
            if key not in self.config_data:
                self.config_data[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config_data[key]:
                        self.config_data[key][sub_key] = sub_value
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"Erro ao carregar config: {e}")
            return {}
    
    
    
    def save_config(self):
        """Salva configuração no arquivo JSON"""
        try:
            # Adiciona timestamp da última atualização
            self.config_data["global"]["last_updated"] = datetime.now().isoformat()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Configuração salva em {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")
    
    # Métodos de acesso Global
    def get_user_email(self) -> str:
        """Obtém email padrão do usuário"""
        return self.config_data["global"].get("user_email", "")
    
    def set_user_email(self, email: str):
        """Define email padrão do usuário"""
        self.config_data["global"]["user_email"] = email
        self.save_config()
    
    def get_default_subdomain(self) -> str:
        """Obtém subdomínio padrão"""
        return self.config_data["global"].get("default_subdomain", "")
    
    def set_default_subdomain(self, subdomain: str):
        """Define subdomínio padrão"""
        self.config_data["global"]["default_subdomain"] = subdomain
        self.save_config()
    
    def get_network_name(self) -> str:
        """Obtém nome da rede Docker"""
        return self.config_data["global"].get("network_name", "")
    
    def set_network_name(self, network_name: str):
        """Define nome da rede Docker"""
        self.config_data["global"]["network_name"] = network_name
        self.save_config()
    
    def get_hostname(self) -> str:
        """Obtém hostname do servidor"""
        return self.config_data["global"].get("hostname", "")
    
    def set_hostname(self, hostname: str):
        """Define hostname do servidor"""
        self.config_data["global"]["hostname"] = hostname
        self.save_config()
    
    def is_cloudflare_auto_dns_enabled(self) -> bool:
        """Verifica se DNS automático está habilitado"""
        return self.config_data["global"].get("cloudflare_auto_dns", False)
    
    def set_cloudflare_auto_dns(self, enabled: bool):
        """Define se DNS automático está habilitado"""
        self.config_data["global"]["cloudflare_auto_dns"] = enabled
        self.save_config()
    
    # Métodos Cloudflare
    def get_cloudflare_config(self) -> Dict[str, str]:
        """Obtém configuração completa do Cloudflare"""
        return self.config_data.get("cloudflare", {})
    
    def set_cloudflare_config(self, api_token: str, zone_id: str, zone_name: str, email: str = None):
        """Define configuração do Cloudflare com Global API Key"""
        cloudflare_config = {
            "api_token": api_token,  # Global API Key
            "zone_id": zone_id,
            "zone_name": zone_name,
            "enabled": True
        }
        
        # Adiciona email se fornecido (necessário para Global API Key)
        if email:
            cloudflare_config["email"] = email
        
        self.config_data["cloudflare"].update(cloudflare_config)
        self.save_config()
    
    # Métodos de Credenciais
    def generate_secure_password(self, length: int = 64) -> str:
        """Gera senha segura com caracteres especiais"""
        # Inclui letras, números e caracteres especiais comuns
        alphabet = string.ascii_letters + string.digits + '@#$%&*'
        
        # Garante que a senha tenha pelo menos um de cada tipo
        password = []
        password.append(secrets.choice(string.ascii_lowercase))
        password.append(secrets.choice(string.ascii_uppercase))
        password.append(secrets.choice(string.digits))
        password.append(secrets.choice('@#$%&*'))
        
        # Preenche o resto com caracteres aleatórios
        for _ in range(length - 4):
            password.append(secrets.choice(alphabet))
        
        # Embaralha para evitar padrão previsível
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def save_app_credentials(self, app_name: str, credentials: Dict[str, Any]):
        """Salva credenciais de uma aplicação"""
        self.logger.debug(f"Salvando credenciais para {app_name}: {list(credentials.keys())}")
        self.config_data["credentials"][app_name] = {
            **credentials,
            "created_at": datetime.now().isoformat()
        }
        self.save_config()
        self.logger.debug(f"Credenciais de {app_name} salvas com sucesso")
    
    def get_app_credentials(self, app_name: str) -> Dict[str, Any]:
        """Obtém credenciais de uma aplicação"""
        creds = self.config_data["credentials"].get(app_name, {})
        if creds:
            self.logger.debug(f"Credenciais encontradas para {app_name}: {list(creds.keys())}")
        else:
            self.logger.debug(f"Nenhuma credencial encontrada para {app_name}")
            self.logger.debug(f"Apps com credenciais: {list(self.config_data['credentials'].keys())}")
        return creds
    
    def save_app_config(self, app_name: str, config: Dict[str, Any]):
        """Salva configuração de uma aplicação"""
        if app_name not in self.config_data["applications"]:
            self.config_data["applications"][app_name] = {}
        
        self.config_data["applications"][app_name].update({
            **config,
            "configured_at": datetime.now().isoformat()
        })
        self.save_config()
    
    def get_app_config(self, app_name: str) -> Dict[str, Any]:
        """Obtém configuração de uma aplicação"""
        return self.config_data["applications"].get(app_name, {})
    
    def is_app_installed(self, app_name: str) -> bool:
        """Verifica se aplicação está instalada"""
        return app_name in self.config_data["applications"]
    
    # Métodos Utilitários
    def suggest_domain(self, app_name: str) -> str:
        """Sugere domínio para uma aplicação"""
        subdomain = self.get_default_subdomain()
        zone_name = self.config_data["cloudflare"].get("zone_name", "")
        
        if subdomain and zone_name:
            # Mapear nomes de apps para prefixos padronizados
            app_prefixes = {
                "portainer": "ptn",
                "chatwoot": "chat",
                "directus": "cms",
                "n8n": "edt",
                "grafana": "monitor",
                "passbolt": "pass",
                "evolution": "evo"
            }
            
            prefix = app_prefixes.get(app_name.lower(), app_name.lower())
            return f"{prefix}.{subdomain}.{zone_name}"
        
        return ""
    
    def get_suggested_email_and_password(self, app_name: str) -> tuple[str, str]:
        """Obtém email e senha sugeridos para uma aplicação"""
        email = self.get_user_email()
        password = self.generate_secure_password()
        return email, password
    
    def export_legacy_format(self, app_name: str) -> str:
        """Exporta dados no formato legado para compatibilidade"""
        app_creds = self.get_app_credentials(app_name)
        app_config = self.get_app_config(app_name)
        
        lines = []
        lines.append(f"🔧 {app_name.upper()}")
        lines.append("─" * (len(app_name) + 5))
        lines.append(f"Instalado em: {app_config.get('configured_at', 'N/A')}")
        
        for key, value in {**app_config, **app_creds}.items():
            if not key.endswith("_at") and key != "created_at":
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtém resumo das configurações"""
        return {
            "total_apps": len(self.config_data["applications"]),
            "cloudflare_enabled": self.config_data["cloudflare"].get("enabled", False),
            "auto_dns_enabled": self.is_cloudflare_auto_dns_enabled(),
            "network_name": self.get_network_name(),
            "hostname": self.get_hostname(),
            "user_email": self.get_user_email(),
            "last_updated": self.config_data["global"].get("last_updated", "N/A")
        }