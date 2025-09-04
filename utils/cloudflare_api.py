#!/usr/bin/env python3
"""
Utilitário para integração com a API da Cloudflare
Usa APENAS Global API Key com Email (como no repositório original)
"""

import json
import requests
import logging
import re
from typing import Dict, Optional, List
from .config_manager import ConfigManager


class CloudflareAPI:
    """Integração com a API da Cloudflare para DNS automático
    
    Usa APENAS Global API Key + Email para autenticação
    """
    
    def __init__(self, config_manager: ConfigManager = None, logger=None):
        # Certifica-se de que logger é sempre um logger válido
        if logger and hasattr(logger, 'debug'):
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
        
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.config = config_manager or ConfigManager()
        
        # Credenciais - APENAS Global API Key
        self.api_key = None
        self.email = None
        self.zone_name = None
        self.zone_id = None
        self.headers = None
        
        self._load_credentials()
    
    def _load_credentials(self):
        """Carrega credenciais do ConfigManager"""
        try:
            cloudflare_config = self.config.get_cloudflare_config()
            
            if not cloudflare_config or not cloudflare_config.get("enabled"):
                self.logger.debug("Cloudflare não está habilitado")
                return
            
            # Carrega credenciais
            self.api_key = cloudflare_config.get("api_token")  # Campo mantido para compatibilidade
            self.email = cloudflare_config.get("email")
            self.zone_name = cloudflare_config.get("zone_name")
            self.zone_id = cloudflare_config.get("zone_id")
            
            # Se tem API key e email, configura headers
            if self.api_key and self.email:
                self.headers = {
                    "X-Auth-Email": self.email,
                    "X-Auth-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                self.logger.debug(f"✅ Cloudflare configurado com Global API Key para {self.zone_name}")
            else:
                if not self.email:
                    self.logger.debug("Email da Cloudflare não encontrado")
                if not self.api_key:
                    self.logger.debug("API Key da Cloudflare não encontrada")
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais Cloudflare: {e}")
    
    def setup_credentials(self, api_key: str, email: str, zone_name: str) -> bool:
        """Configura credenciais da Cloudflare (Global API Key)"""
        self.api_key = api_key
        self.email = email
        self.zone_name = zone_name
        
        self.headers = {
            "X-Auth-Email": self.email,
            "X-Auth-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Testa e obtém zone_id
        if self.get_zone_id():
            self._save_credentials()
            return True
        else:
            self.logger.error("❌ Falha ao validar credenciais Cloudflare")
            return False
    
    def _save_credentials(self):
        """Salva credenciais no ConfigManager"""
        try:
            if not self.zone_name or not self.zone_id or not self.email or not self.api_key:
                self.logger.error("❌ Dados incompletos para salvar")
                return
            
            # Salva no ConfigManager com email
            self.config.set_cloudflare_config(
                api_token=self.api_key,  # Usa o mesmo campo para compatibilidade
                zone_id=self.zone_id,
                zone_name=self.zone_name
            )
            
            # Adiciona o email ao config
            cf_config = self.config.get_cloudflare_config()
            cf_config["email"] = self.email
            self.config.config_data["cloudflare"] = cf_config
            self.config.save_config()
            
            self.logger.info(f"✅ Credenciais Cloudflare salvas (Global API Key)")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
    
    def _log_request(self, method, url, data=None, response=None):
        """Log detalhado de requests para debug"""
        self.logger.debug("=" * 60)
        self.logger.debug(f"🌐 CLOUDFLARE API REQUEST")
        self.logger.debug(f"Method: {method}")
        self.logger.debug(f"URL: {url}")
        
        if data:
            self.logger.debug(f"Request Data: {json.dumps(data, indent=2)}")
        
        if response:
            self.logger.debug(f"Response Status: {response.status_code}")
            try:
                response_json = response.json()
                self.logger.debug(f"Response Body: {json.dumps(response_json, indent=2)}")
            except:
                self.logger.debug(f"Response Body (raw): {response.text}")
        
        self.logger.debug("=" * 60)
    
    def test_connection(self) -> bool:
        """Testa a conexão com a API usando Global API Key"""
        if not self.headers:
            self.logger.error("Credenciais não configuradas")
            return False
        
        try:
            # Teste para Global API Key - endpoint /user
            url = f"{self.base_url}/user"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    user_email = data.get("result", {}).get("email", "")
                    self.logger.info(f"✅ Global API Key válida para {user_email}")
                    return True
                else:
                    self.logger.error(f"❌ Global API Key inválida: {data.get('errors', [])}")
                    return False
            else:
                self.logger.error(f"❌ Erro na verificação da API Key: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro de conexão: {str(e)}")
            return False
    
    def get_zone_id(self) -> bool:
        """Obtém o ID da zona DNS e valida credenciais"""
        if not self.headers or not self.zone_name:
            self.logger.error("❌ Credenciais ou zona não configuradas")
            return False
        
        url = f"{self.base_url}/zones"
        params = {"name": self.zone_name}
        
        try:
            self.logger.debug(f"🔍 Buscando zona: {self.zone_name}")
            
            response = requests.get(url, headers=self.headers, params=params)
            self._log_request("GET", url, params, response)
            
            response.raise_for_status()
            
            data = response.json()
            if data["success"] and data["result"]:
                self.zone_id = data["result"][0]["id"]
                self.logger.info(f"✅ Zona encontrada: {self.zone_name} (ID: {self.zone_id})")
                return True
            else:
                self.logger.error(f"❌ Zona não encontrada: {self.zone_name}")
                if data.get("errors"):
                    for error in data["errors"]:
                        self.logger.error(f"   Erro: {error}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao buscar zona: {e}")
            return False
    
    def list_zones(self) -> List[Dict]:
        """Lista todas as zonas DNS disponíveis na conta"""
        if not self.headers:
            self.logger.error("❌ Credenciais não configuradas")
            return []
        
        url = f"{self.base_url}/zones"
        page = 1
        per_page = 50
        zones = []
        
        try:
            self.logger.debug("🔍 Listando zonas disponíveis...")
            
            while True:
                params = {"page": page, "per_page": per_page}
                response = requests.get(url, headers=self.headers, params=params)
                self._log_request("GET", url, params, response)
                response.raise_for_status()
                
                data = response.json()
                if not data.get("success"):
                    self.logger.error(f"❌ Erro na página {page}: {data.get('errors', [])}")
                    break
                
                results = data.get("result", []) or []
                for zone in results:
                    zones.append({
                        "id": zone.get("id"),
                        "name": zone.get("name"),
                        "status": zone.get("status")
                    })
                
                # Verifica paginação
                info = data.get("result_info", {}) or {}
                total_pages = info.get("total_pages", 1)
                
                self.logger.debug(f"📄 Página {page}/{total_pages} - {len(results)} zonas")
                
                if page >= total_pages:
                    break
                page += 1
            
            if zones:
                self.logger.info(f"✅ Encontradas {len(zones)} zonas")
            else:
                self.logger.warning("⚠️ Nenhuma zona encontrada")
            
            return zones
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao listar zonas: {e}")
            return []
    
    def list_dns_records(self, record_type: str = None) -> List[Dict]:
        """Lista todos os registros DNS da zona"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return []
        
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        params = {}
        if record_type:
            params["type"] = record_type
        
        try:
            self.logger.debug(f"📋 Listando registros DNS (tipo: {record_type or 'todos'})")
            
            response = requests.get(url, headers=self.headers, params=params)
            self._log_request("GET", url, params, response)
            
            response.raise_for_status()
            
            data = response.json()
            if data["success"]:
                records = data["result"]
                self.logger.info(f"📋 Encontrados {len(records)} registros DNS")
                
                for record in records:
                    self.logger.debug(
                        f"  - {record['name']} ({record['type']}) -> {record['content']}"
                    )
                
                return records
            else:
                self.logger.error(f"❌ Erro ao listar registros: {data.get('errors', [])}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao listar registros: {e}")
            return []
    
    def check_dns_record(self, name: str, record_type: str = "CNAME") -> bool:
        """Verifica se um registro DNS específico existe"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return False
        
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        params = {"name": name, "type": record_type}
        
        try:
            self.logger.debug(f"🔍 Verificando registro: {name} ({record_type})")
            
            response = requests.get(url, headers=self.headers, params=params)
            self._log_request("GET", url, params, response)
            
            response.raise_for_status()
            
            data = response.json()
            if data["success"] and data["result"]:
                record = data["result"][0]
                self.logger.info(f"✅ Registro encontrado: {name} -> {record['content']}")
                return True
            else:
                self.logger.info(f"❌ Registro não encontrado: {name}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao verificar registro: {e}")
            return False
    
    def create_cname_record(self, name: str, target: str, proxied: bool = False) -> bool:
        """Cria um registro CNAME"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return False
        
        # Verifica se já existe
        if self.check_dns_record(name, "CNAME"):
            self.logger.info(f"✅ Registro CNAME já existe: {name}")
            return True
        
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        data = {
            "type": "CNAME",
            "name": name,
            "content": target,
            "ttl": 1,  # Auto TTL
            "proxied": proxied
        }
        
        try:
            self.logger.info(f"🔧 Criando registro CNAME: {name} -> {target}")
            
            response = requests.post(url, headers=self.headers, json=data)
            self._log_request("POST", url, data, response)
            
            if response.status_code == 400:
                # Registro já existe
                self.logger.info(f"✅ Registro CNAME já existe: {name}")
                return True
            
            response.raise_for_status()
            
            result = response.json()
            if result["success"]:
                self.logger.info(f"✅ Registro CNAME criado: {name} -> {target}")
                return True
            else:
                self.logger.error(f"❌ Erro ao criar registro: {result.get('errors', [])}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao criar registro: {e}")
            return False
    
    def create_a_record(self, name: str, ip: str, proxied: bool = True, comment: str = None) -> bool:
        """Cria um registro A"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return False
        
        # Verifica se já existe
        existing = self._find_dns_records(name, "A")
        if existing:
            self.logger.info(f"✅ Registro A já existe para {name}")
            return True
        
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        data = {
            "type": "A",
            "name": name,
            "content": ip,
            "ttl": 1,  # Auto TTL
            "proxied": proxied
        }
        
        if comment:
            data["comment"] = comment
        
        try:
            self.logger.info(f"🔧 Criando registro A: {name} -> {ip}")
            
            response = requests.post(url, headers=self.headers, json=data)
            self._log_request("POST", url, data, response)
            
            if response.status_code == 400:
                self.logger.info(f"✅ Registro A já existe: {name}")
                return True
            
            response.raise_for_status()
            
            result = response.json()
            if result.get("success"):
                self.logger.info(f"✅ Registro A criado: {name} -> {ip}")
                return True
            else:
                self.logger.error(f"❌ Erro ao criar registro A: {result.get('errors', [])}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao criar registro A: {e}")
            return False
    
    def _find_dns_records(self, name: str, record_type: str) -> List[Dict]:
        """Retorna a lista de registros que casam com nome e tipo"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return []
        
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        params = {"name": name, "type": record_type}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            self._log_request("GET", url, params, response)
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                return data.get("result", [])
            return []
            
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Erro ao buscar registros: {e}")
            return []
    
    def _update_dns_record(self, record_id: str, data: Dict) -> bool:
        """Atualiza um registro DNS existente"""
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}"
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            self._log_request("PUT", url, data, response)
            response.raise_for_status()
            
            result = response.json()
            if result.get("success"):
                self.logger.info("✅ Registro DNS atualizado com sucesso")
                return True
            
            self.logger.error(f"❌ Falha ao atualizar registro: {result.get('errors', [])}")
            return False
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao atualizar registro: {e}")
            return False
    
    def ensure_a_record(self, name: str, ip: str = None, proxied: bool = True, comment: str = None) -> bool:
        """Garante que um registro A exista e aponte para o IP correto"""
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Zone ID não encontrado")
                return False
        
        if not ip:
            ip = self.get_public_ip()
        
        if not ip:
            self.logger.error("❌ IP não especificado e não foi possível detectar automaticamente")
            return False
        
        records = self._find_dns_records(name, "A")
        
        if not records:
            # Cria novo registro
            return self.create_a_record(name, ip, proxied=proxied, comment=comment)
        
        # Verifica se precisa atualizar
        record = records[0]
        needs_update = (
            record.get("content") != ip or
            record.get("proxied") != proxied or
            (comment is not None and record.get("comment") != comment)
        )
        
        if not needs_update:
            self.logger.info(f"✅ Registro A já configurado corretamente: {name} -> {ip}")
            return True
        
        # Atualiza registro existente
        data = {
            "type": "A",
            "name": name,
            "content": ip,
            "ttl": 1,
            "proxied": proxied
        }
        
        if comment is not None:
            data["comment"] = comment
        
        self.logger.info(f"🔧 Atualizando registro A: {name} -> {ip}")
        return self._update_dns_record(record.get("id"), data)
    
    def ensure_cname_record(self, name: str, target: str, proxied: bool = False) -> bool:
        """Garante que um registro CNAME exista"""
        self.logger.info(f"🔍 Garantindo registro CNAME: {name} -> {target}")
        
        if self.check_dns_record(name, "CNAME"):
            self.logger.info(f"✅ Registro já existe: {name}")
            return True
        else:
            self.logger.info(f"🔧 Criando novo registro: {name} -> {target}")
            return self.create_cname_record(name, target, proxied=proxied)
    
    def get_public_ip(self) -> Optional[str]:
        """Obtém o IP público da máquina atual"""
        endpoints = [
            "https://api.ipify.org",
            "https://ipv4.icanhazip.com",
            "https://ifconfig.me/ip",
        ]
        
        ipv4_regex = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
        
        for url in endpoints:
            try:
                self.logger.debug(f"🔍 Buscando IP público em {url}...")
                resp = requests.get(url, timeout=5)
                ip = resp.text.strip()
                
                if ipv4_regex.match(ip):
                    self.logger.info(f"✅ IP público detectado: {ip}")
                    return ip
                    
            except Exception as e:
                self.logger.debug(f"⚠️ Falha ao obter IP em {url}: {e}")
        
        self.logger.error("❌ Não foi possível detectar o IP público")
        return None
    
    def setup_dns_for_service(self, service_name: str, domains: List[str], 
                            target_domain: str = None, record_type: str = "A") -> bool:
        """Configura DNS para um serviço específico
        
        Por padrão usa registro A (direto para IP) em vez de CNAME
        """
        self.logger.info(f"🌐 Configurando DNS para {service_name}")
        
        if not self.zone_id:
            if not self.get_zone_id():
                self.logger.error("❌ Falha ao obter Zone ID")
                return False
        
        success = True
        
        if record_type == "CNAME":
            # Para CNAME, precisa de um target_domain
            if not target_domain:
                # Tenta obter do Portainer no ConfigManager
                portainer_config = self.config.get_app_config('portainer')
                if portainer_config and portainer_config.get('domain'):
                    target_domain = portainer_config['domain']
                else:
                    self.logger.error("❌ Target domain não especificado e Portainer não configurado")
                    return False
            
            for domain in domains:
                self.logger.info(f"🔧 Processando CNAME: {domain} -> {target_domain}")
                if not self.ensure_cname_record(domain, target_domain):
                    self.logger.error(f"❌ Falha ao configurar CNAME para {domain}")
                    success = False
                    
        else:  # Default: registro A
            # Para registro A, detecta o IP automaticamente
            ip = self.get_public_ip()
            if not ip:
                self.logger.error("❌ Não foi possível detectar IP público")
                return False
            
            for domain in domains:
                self.logger.info(f"🔧 Processando registro A: {domain} -> {ip}")
                if not self.ensure_a_record(domain, ip, comment=f"Auto-created for {service_name}"):
                    self.logger.error(f"❌ Falha ao configurar registro A para {domain}")
                    success = False
        
        if success:
            self.logger.info(f"✅ DNS configurado com sucesso para {service_name}")
        else:
            self.logger.warning(f"⚠️ Alguns registros DNS falharam para {service_name}")
        
        return success
    
    def suggest_domain_for_app(self, app_name: str) -> str:
        """Sugere domínio para uma aplicação usando ConfigManager"""
        return self.config.suggest_domain(app_name)
    
    def create_app_dns_record(self, app_name: str, domain: str = None, 
                            record_type: str = "A", target_domain: str = None) -> bool:
        """Cria registro DNS para uma aplicação específica"""
        if not self.is_configured():
            self.logger.error("❌ Cloudflare não configurado")
            return False
        
        # Usa domínio sugerido se não fornecido
        if not domain:
            domain = self.suggest_domain_for_app(app_name)
        
        if not domain:
            self.logger.error("❌ Não foi possível determinar domínio para a aplicação")
            return False
        
        success = False
        
        if record_type == "A":
            # Detecta IP público do servidor
            ip_address = self.get_public_ip()
            if not ip_address:
                self.logger.error("❌ Não foi possível detectar IP público do servidor")
                return False
            
            # Cria registro A
            success = self.ensure_a_record(
                domain, 
                ip_address,
                comment=f"Auto-created for {app_name} via LivChatSetup"
            )
            
            if success:
                # Salva no ConfigManager
                self.config.add_dns_record({
                    "app_name": app_name,
                    "domain": domain,
                    "ip": ip_address,
                    "type": "A"
                })
                self.logger.info(f"✅ DNS configurado: {domain} → {ip_address}")
                
        elif record_type == "CNAME":
            if not target_domain:
                self.logger.error("❌ Target domain é obrigatório para CNAME")
                return False
            
            success = self.ensure_cname_record(domain, target_domain)
            
            if success:
                # Salva no ConfigManager
                self.config.add_dns_record({
                    "app_name": app_name,
                    "domain": domain,
                    "target": target_domain,
                    "type": "CNAME"
                })
                self.logger.info(f"✅ DNS configurado: {domain} → {target_domain}")
        
        else:
            self.logger.error(f"❌ Tipo de registro não suportado: {record_type}")
        
        return success
    
    def is_configured(self) -> bool:
        """Verifica se a API está configurada e funcional"""
        has_auth = bool(self.headers and self.api_key and self.email)
        return has_auth and bool(self.zone_name) and bool(self.zone_id or self.get_zone_id())
    
    def get_auth_info(self) -> Dict:
        """Retorna informações sobre a autenticação configurada"""
        if not self.is_configured():
            return {
                "configured": False,
                "auth_type": "global_key",
                "zone_name": None,
                "zone_id": None,
                "email": None
            }
        
        return {
            "configured": True,
            "auth_type": "global_key",  # SEMPRE Global API Key
            "zone_name": self.zone_name,
            "zone_id": self.zone_id,
            "email": self.email
        }


def get_cloudflare_api(logger=None, config_manager: ConfigManager = None) -> Optional[CloudflareAPI]:
    """Factory function - Cria instância do CloudflareAPI
    
    Returns:
        CloudflareAPI configurado ou None se não houver configuração
    """
    if not config_manager:
        config_manager = ConfigManager()
    
    cf = CloudflareAPI(config_manager, logger)
    
    if cf.is_configured():
        # Testa a conexão
        if cf.test_connection():
            if logger:
                logger.info(f"✅ Cloudflare configurado com Global API Key")
            return cf
        else:
            if logger:
                logger.error(f"❌ Falha na configuração Cloudflare")
            return None
    
    if logger:
        logger.info("🔧 Cloudflare não configurado. Configure via menu principal.")
    
    return None