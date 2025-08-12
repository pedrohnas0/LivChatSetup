#!/usr/bin/env python3
"""
Utilitário para integração com a API da Cloudflare
Módulo reutilizável para gerenciamento de DNS automático
"""

import os
import json
import requests
import logging
import re
from datetime import datetime

class CloudflareAPI:
    """Integração com a API da Cloudflare para DNS automático"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.credentials_file = "/root/dados_vps/dados_cloudflare"
        
        # Carrega credenciais
        self.api_key = None
        self.email = None
        self.zone_name = None
        self.zone_id = None
        
        self._load_credentials()
        
        if self.api_key and self.email:
            self.headers = {
                "X-Auth-Email": self.email,
                "X-Auth-Key": self.api_key,
                "Content-Type": "application/json"
            }
        else:
            self.headers = None
    
    def _load_credentials(self):
        """Carrega credenciais do arquivo de configuração"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('API_KEY:'):
                            self.api_key = line.split(':', 1)[1].strip()
                        elif line.startswith('EMAIL:'):
                            self.email = line.split(':', 1)[1].strip()
                        elif line.startswith('ZONE:'):
                            self.zone_name = line.split(':', 1)[1].strip()
                        elif line.startswith('ZONE_ID:'):
                            self.zone_id = line.split(':', 1)[1].strip()
                
                self.logger.debug(f"✅ Credenciais Cloudflare carregadas: {self.email} - {self.zone_name}")
            else:
                self.logger.debug("❌ Arquivo de credenciais Cloudflare não encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais Cloudflare: {e}")
    
    def _save_credentials(self):
        """Salva credenciais no arquivo de configuração"""
        try:
            os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
            
            with open(self.credentials_file, 'w') as f:
                f.write(f"# Credenciais da Cloudflare - Gerado em {datetime.now()}\n")
                f.write(f"API_KEY: {self.api_key}\n")
                f.write(f"EMAIL: {self.email}\n")
                f.write(f"ZONE: {self.zone_name}\n")
                f.write(f"ZONE_ID: {self.zone_id}\n")
            
            self.logger.info(f"✅ Credenciais Cloudflare salvas em {self.credentials_file}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais Cloudflare: {e}")
    
    def setup_credentials(self, api_key, email, zone_name):
        """Configura credenciais da Cloudflare"""
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
        
        try:
            self.logger.debug("🔍 Listando zonas disponíveis...")
            
            response = requests.get(url, headers=temp_headers)
            self._log_request("GET", url, None, response)
            
            response.raise_for_status()
            
            data = response.json()
            if data["success"] and data["result"]:
                zones = []
                for zone in data["result"]:
                    zones.append({
                        "id": zone["id"],
                        "name": zone["name"],
                        "status": zone["status"]
                    })
                
                self.logger.info(f"✅ Encontradas {len(zones)} zonas")
                return zones
            else:
                self.logger.error("❌ Nenhuma zona encontrada")
                if data.get("errors"):
                    for error in data["errors"]:
                        self.logger.error(f"   Erro: {error}")
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
        """Obtém o host do Portainer salvo em /root/dados_vps/dados_portainer para usar como alvo CNAME."""
        try:
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
            self.logger.error(f"❌ Erro ao buscar registros DNS: {e}")
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
        return (self.api_key and self.email and self.zone_name and 
                self.headers and (self.zone_id or self.get_zone_id()))

def get_cloudflare_api(logger=None):
    """Factory function para obter instância configurada da CloudflareAPI"""
    cf = CloudflareAPI(logger)
    
    if not cf.is_configured():
        logger.info("🔧 Configurando credenciais Cloudflare...")
        
        # Coleta credenciais do usuário
        api_key = input("Digite sua API Key da Cloudflare: ").strip()
        email = input("Digite seu email da Cloudflare: ").strip()
        
        if not api_key or not email:
            logger.error("❌ API Key e email são obrigatórios")
            return None
        
        # Testa credenciais listando zonas disponíveis
        temp_cf = CloudflareAPI(logger)
        temp_cf.api_key = api_key
        temp_cf.email = email
        
        zones = temp_cf.list_zones()
        if not zones:
            logger.error("❌ Falha ao conectar com Cloudflare ou nenhuma zona encontrada")
            return None
        
        logger.info("\n📋 Zonas disponíveis:")
        for i, zone in enumerate(zones, 1):
            logger.info(f"  [{i}] {zone['name']} (ID: {zone['id']})")
        
        while True:
            try:
                choice = input(f"\nEscolha a zona [1-{len(zones)}]: ").strip()
                zone_idx = int(choice) - 1
                
                if 0 <= zone_idx < len(zones):
                    selected_zone = zones[zone_idx]['name']
                    break
                else:
                    print(f"❌ Opção inválida. Digite um número entre 1 e {len(zones)}")
            except ValueError:
                print("❌ Digite um número válido")
        
        if cf.setup_credentials(api_key, email, selected_zone):
            logger.info("✅ Cloudflare configurado com sucesso")
        else:
            logger.error("❌ Falha ao configurar Cloudflare")
            return None
    
    return cf
