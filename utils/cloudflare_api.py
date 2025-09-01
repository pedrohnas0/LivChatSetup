#!/usr/bin/env python3
"""
Utilitário para integração com a API da Cloudflare v2.0
Módulo reutilizável integrado ao ConfigManager
"""

import os
import json
import requests
import logging
import re
from datetime import datetime
from typing import Dict, Optional, List
from .config_manager import ConfigManager

class CloudflareAPI:
    """Integração com a API da Cloudflare para DNS automático v2.0
    
    Integrado ao ConfigManager para configurações centralizadas
    """
    
    def __init__(self, config_manager: ConfigManager = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.config = config_manager or ConfigManager()
        
        # Carrega credenciais do ConfigManager
        self.api_token = None  # Para tokens Bearer
        self.api_key = None    # Para API Keys tradicionais
        self.email = None      # Necessário para API Keys
        self.zone_name = None
        self.zone_id = None
        
        self._load_credentials()
        
        # Configura headers baseado no tipo de autenticação
        if self.api_token:
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
        elif self.api_key and self.email:
            self.headers = {
                "X-Auth-Email": self.email,
                "X-Auth-Key": self.api_key,
                "Content-Type": "application/json"
            }
        else:
            self.headers = None
    
    def _load_credentials(self):
        """Carrega credenciais do ConfigManager"""
        try:
            cloudflare_config = self.config.get_cloudflare_config()
            
            if cloudflare_config.get("enabled"):
                # Tenta carregar como Token primeiro
                self.api_token = cloudflare_config.get("api_token")
                # Se não for Token, tenta API Key + Email
                if not self.api_token:
                    self.api_key = cloudflare_config.get("api_token")  # api_token pode ser api_key
                    self.email = cloudflare_config.get("email")
                
                self.zone_name = cloudflare_config.get("zone_name")
                self.zone_id = cloudflare_config.get("zone_id")
                
                auth_type = "Token" if self.api_token else "API Key"
                self.logger.debug(f"✅ Credenciais Cloudflare carregadas ({auth_type}): {self.zone_name}")
            else:
                # Tenta migração das credenciais antigas
                self._migrate_old_credentials()
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais Cloudflare: {e}")
    
    def _migrate_old_credentials(self):
        """Migra credenciais do arquivo antigo para o ConfigManager"""
        old_file = "/root/dados_vps/dados_cloudflare"
        
        if not os.path.exists(old_file):
            self.logger.debug("❌ Credenciais Cloudflare não encontradas")
            return
            
        try:
            api_key = None
            email = None
            zone_name = None
            zone_id = None
            
            with open(old_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('API_KEY:'):
                        api_key = line.split(':', 1)[1].strip()
                    elif line.startswith('API Token:'):  # Compatibilidade
                        api_key = line.split(':', 1)[1].strip()
                    elif line.startswith('EMAIL:'):
                        email = line.split(':', 1)[1].strip()
                    elif line.startswith('ZONE:') or line.startswith('Zone Name:'):
                        zone_name = line.split(':', 1)[1].strip()
                    elif line.startswith('ZONE_ID:') or line.startswith('Zone ID:'):
                        zone_id = line.split(':', 1)[1].strip()
            
            if api_key and zone_name and zone_id:
                # Salva no ConfigManager (api_token field pode conter API Key)
                self.config.set_cloudflare_config(api_key, zone_id, zone_name)
                # Adiciona email se disponível
                if email:
                    # Estende ConfigManager para suportar email
                    cf_config = self.config.get_cloudflare_config()
                    cf_config["email"] = email
                    self.config.config_data["cloudflare"] = cf_config
                    self.config.save_config()
                
                self.api_key = api_key
                self.email = email
                self.zone_name = zone_name
                self.zone_id = zone_id
                
                self.logger.info("✅ Credenciais Cloudflare migradas para ConfigManager")
                
        except Exception as e:
            self.logger.error(f"Erro ao migrar credenciais antigas: {e}")
    
    def _save_credentials(self):
        """Salva credenciais no ConfigManager"""
        try:
            if self.api_token and self.zone_name and self.zone_id:
                self.config.set_cloudflare_config(self.api_token, self.zone_id, self.zone_name)
                self.logger.info("✅ Credenciais Cloudflare salvas no ConfigManager")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais Cloudflare: {e}")
    
    def setup_credentials(self, api_token: str, zone_name: str) -> bool:
        """Configura credenciais da Cloudflare"""
        self.api_token = api_token
        self.zone_name = zone_name
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Testa e obtém zone_id
        zone_id = self.get_zone_id(zone_name)
        if zone_id:
            self.zone_id = zone_id
            self._save_credentials()
            return True
        else:
            self.logger.error("❌ Falha ao validar credenciais Cloudflare")
            return False
    
    def _log_request(self, method, url, data=None, response=None):
        """Log detalhado de requests para debug"""
        self.logger.debug("=" * 60)
        self.logger.debug(f"🌐 CLOUDFLARE API REQUEST")
        self.logger.debug(f"Method: {method}")
        self.logger.debug(f"URL: {url}")
        self.logger.debug(f"Headers: {json.dumps(self.headers, indent=2)}")
        
        if data:
            self.logger.debug(f"Request Data: {json.dumps(data, indent=2)}")
        
        if response:
            self.logger.debug(f"Response Status: {response.status_code}")
            self.logger.debug(f"Response Headers: {dict(response.headers)}")
            try:
                response_json = response.json()
                self.logger.debug(f"Response Body: {json.dumps(response_json, indent=2)}")
            except:
                self.logger.debug(f"Response Body (raw): {response.text}")
        
        self.logger.debug("=" * 60)
    
    def list_zones(self):
        """Lista todas as zonas DNS disponíveis na conta"""
        if not self.api_key or not self.email:
            self.logger.error("❌ API Key e email são obrigatórios")
            return []
        
        # Configura headers temporariamente se necessário
        temp_headers = {
            "X-Auth-Email": self.email,
            "X-Auth-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/zones"
        page = 1
        per_page = 50  # limite típico suportado pela API
        zones = []
        
        try:
            self.logger.debug("🔍 Listando zonas disponíveis (com paginação)...")
            while True:
                params = {"page": page, "per_page": per_page}
                response = requests.get(url, headers=temp_headers, params=params)
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
                info = data.get("result_info", {}) or {}
                total_pages = info.get("total_pages")
                self.logger.debug(f"📄 Página {page}/{total_pages or '?'} - itens: {len(results)}")
                # Condições de parada
                if total_pages:
                    if page >= total_pages:
                        break
                else:
                    if len(results) < per_page:
                        break
                page += 1
            if zones:
                self.logger.info(f"✅ Encontradas {len(zones)} zonas (paginadas)")
                return zones
            else:
                self.logger.error("❌ Nenhuma zona encontrada")
                return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao listar zonas: {e}")
            return []
    
    def get_zone_id(self):
        """Obtém o ID da zona DNS"""
        if not self.headers:
            self.logger.error("❌ Credenciais Cloudflare não configuradas")
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
    
    def list_dns_records(self, record_type=None):
        """Lista todos os registros DNS da zona"""
        if not self.zone_id:
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
                    self.logger.debug(f"  - {record['name']} ({record['type']}) -> {record['content']}")
                
                return records
            else:
                self.logger.error(f"❌ Erro ao listar registros: {data.get('errors', [])}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao listar registros: {e}")
            return []
    
    def check_dns_record(self, name, record_type="CNAME"):
        """Verifica se um registro DNS específico existe"""
        if not self.zone_id:
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
    
    def create_cname_record(self, name, target):
        """Cria um registro CNAME (ou verifica se já existe)"""
        if not self.zone_id:
            self.logger.error("❌ Zone ID não encontrado")
            return False
        
        # Primeiro verifica se o registro já existe
        if self.check_dns_record(name, "CNAME"):
            self.logger.info(f"✅ Registro CNAME já existe: {name} -> {target}")
            return True
            
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
        data = {
            "type": "CNAME",
            "name": name,
            "content": target,
            "ttl": 1  # Auto TTL
        }
        
        try:
            self.logger.info(f"🔧 Criando registro CNAME: {name} -> {target}")
            
            response = requests.post(url, headers=self.headers, json=data)
            self._log_request("POST", url, data, response)
            
            if response.status_code == 400:
                # Registro já existe, considerar como sucesso
                self.logger.info(f"✅ Registro CNAME já existe: {name} -> {target}")
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
    
    def ensure_cname_record(self, name, target):
        """Garante que um registro CNAME existe, criando se necessário"""
        self.logger.info(f"🔍 Garantindo registro CNAME: {name} -> {target}")
        
        if self.check_dns_record(name, "CNAME"):
            self.logger.info(f"✅ Registro já existe: {name}")
            return True
        else:
            self.logger.info(f"🔧 Criando novo registro: {name} -> {target}")
            return self.create_cname_record(name, target)
    
    def _get_portainer_cname_target(self):
        """Obtém o host do Portainer do ConfigManager para usar como alvo CNAME."""
        try:
            # Primeiro tenta obter do ConfigManager
            if self.config_manager:
                portainer_config = self.config_manager.get_app_config("portainer")
                if portainer_config and portainer_config.get("domain"):
                    domain = portainer_config["domain"]
                    # Remove esquema e path, mantendo apenas o host
                    domain = domain.replace('https://', '').replace('http://', '')
                    if '/' in domain:
                        domain = domain.split('/', 1)[0]
                    return domain
            
            # Fallback para arquivo legado se ConfigManager não tiver a informação
            creds_path = "/root/dados_vps/dados_portainer"
            if not os.path.exists(creds_path):
                return None
            with open(creds_path, 'r') as f:
                for line in f:
                    if line.startswith('Dominio do portainer:'):
                        val = line.split(':', 1)[1].strip()
                        # Remove esquema e path, mantendo apenas o host
                        val = val.replace('https://', '').replace('http://', '')
                        if '/' in val:
                            val = val.split('/', 1)[0]
                        return val if val else None
        except Exception:
            return None
        return None

    def setup_dns_for_service(self, service_name, domains, target_domain=None):
        """Configura DNS para um serviço específico.
        Se target_domain não for informado, utiliza o domínio do Portainer salvo (mesmo alvo para todas as stacks).
        """
        self.logger.info(f"🌐 Configurando DNS para {service_name}")
        
        if not self.zone_id and not self.get_zone_id():
            self.logger.error("❌ Falha ao obter Zone ID")
            return False
        
        # Determina o alvo dinamicamente, se não informado
        if not target_domain:
            target_domain = self._get_portainer_cname_target()
            if not target_domain:
                self.logger.error("❌ Alvo CNAME não definido e não foi possível obter o domínio do Portainer. Configure o Portainer primeiro.")
                return False
        
        success = True
        for domain in domains:
            self.logger.info(f"🔧 Processando domínio: {domain} -> {target_domain}")
            if not self.ensure_cname_record(domain, target_domain):
                self.logger.error(f"❌ Falha ao configurar DNS para {domain}")
                success = False
        
        if success:
            self.logger.info(f"✅ DNS configurado com sucesso para {service_name}")
        else:
            self.logger.warning(f"⚠️ Alguns registros DNS falharam para {service_name}")
        
        return success

    def get_public_ip(self):
        """Obtém o IP público da máquina atual (IPv4)."""
        endpoints = [
            "https://api.ipify.org",
            "https://ipv4.icanhazip.com",
            "https://ifconfig.me/ip",
        ]
        ipv4_regex = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
        for url in endpoints:
            try:
                self.logger.debug(f"🔍 Buscando IP público em {url} ...")
                resp = requests.get(url, timeout=5)
                ip = resp.text.strip()
                if ipv4_regex.match(ip):
                    self.logger.info(f"✅ IP público detectado: {ip}")
                    return ip
            except Exception as e:
                self.logger.debug(f"⚠️ Falha ao obter IP em {url}: {e}")
        self.logger.error("❌ Não foi possível detectar o IP público")
        return None

    def _find_dns_records(self, name, record_type):
        """Retorna a lista de registros que casam com nome e tipo."""
        if not self.zone_id and not self.get_zone_id():
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
            self.logger.debug(f"Erro ao buscar registros DNS (pode ser normal): {e}")
            return []

    def _update_dns_record(self, record_id, data):
        """Atualiza um registro DNS existente pelo ID (PUT)."""
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

    def create_a_record(self, name, ip, proxied=True, comment=None):
        """Cria um registro A"""
        if not self.zone_id and not self.get_zone_id():
            self.logger.error("❌ Zone ID não encontrado")
            return False

        # Se já existir, considerar sucesso
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
            "proxied": proxied,
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
            self.logger.error(f"❌ Erro ao criar registro A: {result.get('errors', [])}")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Erro ao criar registro A: {e}")
            return False

    def ensure_a_record(self, name, ip=None, proxied=True, comment=None):
        """Garante que um registro A aponte para o IP desejado (criando ou atualizando)."""
        if not self.zone_id and not self.get_zone_id():
            self.logger.error("❌ Zone ID não encontrado")
            return False

        if not ip:
            ip = self.get_public_ip()
        if not ip:
            return False

        records = self._find_dns_records(name, "A")
        if not records:
            return self.create_a_record(name, ip, proxied=proxied, comment=comment)

        # Se existir, verificar se precisa atualizar
        record = records[0]
        needs_update = (
            record.get("content") != ip or
            ("proxied" in record and record.get("proxied") != proxied) or
            (comment is not None and record.get("comment") != comment)
        )

        if not needs_update:
            self.logger.info(f"✅ Registro A já configurado corretamente: {name} -> {ip}")
            return True

        data = {
            "type": "A",
            "name": name,
            "content": ip,
            "ttl": 1,
            "proxied": proxied,
        }
        if comment is not None:
            data["comment"] = comment

        self.logger.info(f"🔧 Atualizando registro A: {name} -> {ip}")
        return self._update_dns_record(record.get("id"), data)

    def is_configured(self):
        """Verifica se a API está configurada e funcional"""
        has_auth = (self.api_token or (self.api_key and self.email))
        return (has_auth and self.zone_name and 
                self.headers and (self.zone_id or self.get_zone_id()))

    def suggest_domain_for_app(self, app_name: str) -> str:
        """Sugere domínio para uma aplicação usando ConfigManager"""
        return self.config.suggest_domain(app_name)
    
    def create_app_dns_record(self, app_name: str, domain: str = None) -> bool:
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
        
        # Detecta IP público do servidor
        ip_address = self._detect_server_ip()
        if not ip_address:
            self.logger.error("❌ Não foi possível detectar IP público do servidor")
            return False
        
        # Cria registro A
        success = self.ensure_a_record(domain, ip_address, 
                                     comment=f"Auto-created for {app_name} via LivChatSetup")
        
        if success:
            # Salva no ConfigManager
            self.config.add_dns_record({
                "app_name": app_name,
                "domain": domain,
                "ip": ip_address,
                "type": "A"
            })
            
            self.logger.info(f"✅ DNS configurado: {domain} → {ip_address}")
        
        return success
    
    def _detect_server_ip(self) -> Optional[str]:
        """Detecta IP público do servidor usando múltiplos serviços"""
        try:
            services = [
                "https://api.ipify.org",
                "https://ipinfo.io/ip", 
                "https://icanhazip.com"
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=10)
                    if response.status_code == 200:
                        ip = response.text.strip()
                        # Validação básica de IP
                        import ipaddress
                        ipaddress.ip_address(ip)
                        return ip
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Erro ao detectar IP: {e}")
        
        return None
    
    def test_api_connection(self) -> bool:
        """Testa conexão com a API Cloudflare usando token"""
        if not self.headers:
            return False
        
        try:
            url = f"{self.base_url}/user/tokens/verify"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.logger.info("✅ Token Cloudflare válido")
                    return True
            
            self.logger.error(f"❌ Token inválido: {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao testar token: {e}")
            return False


def get_cloudflare_api(logger=None, config_manager: ConfigManager = None):
    """Factory function v2.0 - integrado ao ConfigManager"""
    if not config_manager:
        config_manager = ConfigManager()
        
    cf = CloudflareAPI(config_manager, logger)
    
    if not cf.is_configured():
        # Verifica se o ConfigManager já tem configurações válidas
        try:
            cloudflare_config = config_manager.get_cloudflare_config()
            if cloudflare_config and cloudflare_config.get("enabled") and cloudflare_config.get("api_token") and cloudflare_config.get("zone_name"):
                # Tenta configurar com dados existentes
                if cf.setup_credentials(cloudflare_config["api_token"], cloudflare_config["zone_name"]):
                    if logger:
                        logger.info("✅ Cloudflare configurado automaticamente")
                    return cf
        except Exception as e:
            if logger:
                logger.debug(f"Erro ao carregar config Cloudflare: {e}")
        
        if logger:
            logger.info("🔧 Cloudflare não configurado. Configure via menu principal.")
        return None
    
    return cf
