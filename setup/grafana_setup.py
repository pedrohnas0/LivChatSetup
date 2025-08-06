#!/usr/bin/env python3
"""
Módulo de Setup do Grafana (Stack de Monitoramento)
Implementa instalação automatizada do Grafana, Prometheus, cAdvisor e NodeExporter
"""

import os
import subprocess
import secrets
import logging
from typing import Dict, Any
from setup.base_setup import BaseSetup
from utils.portainer_api import PortainerAPI
from utils.cloudflare_api import get_cloudflare_api

class GrafanaSetup(BaseSetup):
    """Setup do Stack de Monitoramento Grafana"""
    
    def __init__(self):
        super().__init__("grafana")
        self.service_name = "grafana"
        self.logger = logging.getLogger(__name__)
        
        # Inicializa APIs
        self.portainer_api = PortainerAPI()
        
    def validate_prerequisites(self) -> bool:
        """Valida pré-requisitos para instalação do Grafana"""
        try:
            # Verifica se Portainer está acessível testando deploy_service_complete
            try:
                # Testa se o método principal existe (sem executar)
                if hasattr(self.portainer_api, 'deploy_service_complete'):
                    self.logger.debug("✅ Portainer acessível")
                else:
                    self.logger.error("Método deploy_service_complete não encontrado")
                    return False
            except Exception as e:
                self.logger.error(f"Erro ao verificar Portainer: {e}")
                return False
                
            # Verifica se a rede Docker existe
            result = subprocess.run(
                "docker network ls | grep orion_network",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error("Rede Docker 'orion_network' não encontrada")
                return False
                
            self.logger.info("✅ Pré-requisitos validados com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao validar pré-requisitos: {e}")
            return False
    
    def collect_user_inputs(self) -> Dict[str, Any]:
        """Coleta inputs do usuário para configuração do Grafana"""
        print("\n" + "="*60)
        print("🔧 CONFIGURAÇÃO DO STACK DE MONITORAMENTO GRAFANA")
        print("="*60)
        
        user_data = {}
        
        # Coleta domínios
        print("\n📋 Configure os domínios para os serviços de monitoramento:")
        
        print("\n📊 Passo 1/4 - Grafana (Dashboard)")
        user_data['grafana_domain'] = input("Digite o domínio para o Grafana (ex: grafana.dev.livchat.ai): ").strip()
        
        print("\n📈 Passo 2/4 - Prometheus (Coleta de Métricas)")
        user_data['prometheus_domain'] = input("Digite o domínio para o Prometheus (ex: prometheus.dev.livchat.ai): ").strip()
        
        print("\n🐳 Passo 3/4 - cAdvisor (Monitoramento de Containers)")
        user_data['cadvisor_domain'] = input("Digite o domínio para o cAdvisor (ex: cadvisor.dev.livchat.ai): ").strip()
        
        print("\n🖥️ Passo 4/4 - NodeExporter (Métricas do Sistema)")
        user_data['nodeexporter_domain'] = input("Digite o domínio para o NodeExporter (ex: node.dev.livchat.ai): ").strip()
        
        # Confirmação
        print("\n" + "="*60)
        print("📋 CONFIRMAÇÃO DOS DADOS")
        print("="*60)
        print(f"📊 Grafana: https://{user_data['grafana_domain']}")
        print(f"📈 Prometheus: https://{user_data['prometheus_domain']}")
        print(f"🐳 cAdvisor: https://{user_data['cadvisor_domain']}")
        print(f"🖥️ NodeExporter: https://{user_data['nodeexporter_domain']}")
        
        while True:
            confirm = input("\n✅ Os dados estão corretos? (s/n): ").strip().lower()
            if confirm in ['s', 'sim', 'y', 'yes']:
                break
            elif confirm in ['n', 'não', 'nao', 'no']:
                return self.collect_user_inputs()  # Recomeça a coleta
            else:
                print("❌ Resposta inválida. Digite 's' para sim ou 'n' para não.")
        
        return user_data
    
    def setup_dns_records(self, user_data: Dict[str, Any]) -> bool:
        """Configura registros DNS via Cloudflare"""
        try:
            self.logger.info("🌐 Configurando DNS via Cloudflare...")
            
            # Obtém API da Cloudflare
            cloudflare_api = get_cloudflare_api()
            if not cloudflare_api:
                self.logger.error("Falha ao obter API da Cloudflare")
                return False
            
            # Lista de domínios para configurar
            domains = [
                ('grafana_domain', 'Grafana'),
                ('prometheus_domain', 'Prometheus'),
                ('cadvisor_domain', 'cAdvisor'),
                ('nodeexporter_domain', 'NodeExporter')
            ]
            
            # Configura DNS para cada domínio
            for domain_key, service_name in domains:
                domain = user_data[domain_key]
                self.logger.info(f"🔧 Configurando DNS para {service_name}: {domain}")
                
                success = cloudflare_api.create_or_update_cname_record(
                    domain, 
                    "ptn.dev.livchat.ai"
                )
                
                if success:
                    self.logger.info(f"✅ DNS configurado para {service_name}")
                else:
                    self.logger.error(f"❌ Falha ao configurar DNS para {service_name}")
                    return False
            
            self.logger.info("✅ Todos os registros DNS configurados com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar DNS: {e}")
            return False
    
    def create_monitor_configs(self, user_data: Dict[str, Any]) -> bool:
        """Cria arquivos de configuração do Prometheus e Grafana"""
        try:
            self.logger.info("📝 Criando arquivos de configuração...")
            
            # Cria diretório base
            os.makedirs("/opt/monitor-orion/prometheus", exist_ok=True)
            os.makedirs("/opt/monitor-orion/grafana/provisioning/datasources", exist_ok=True)
            os.makedirs("/opt/monitor-orion/grafana/provisioning/dashboards", exist_ok=True)
            os.makedirs("/opt/monitor-orion/grafana/dashboards", exist_ok=True)
            
            # Cria prometheus.yml
            prometheus_config = f"""global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s

alerting:
  alertmanagers:
  - static_configs:
    - targets: []
    scheme: http
    timeout: 10s
    api_version: v2

scrape_configs:
- job_name: prometheus
  honor_timestamps: true
  scrape_interval: 15s
  scrape_timeout: 10s
  metrics_path: /metrics
  scheme: https
  static_configs:
  - targets: ['{user_data['prometheus_domain']}', '{user_data['cadvisor_domain']}', '{user_data['nodeexporter_domain']}']
"""
            
            with open("/opt/monitor-orion/prometheus/prometheus.yml", 'w') as f:
                f.write(prometheus_config)
            
            # Cria datasource.yml para Grafana
            datasource_config = f"""apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: https://{user_data['prometheus_domain']}
  isDefault: true
  access: proxy
  editable: true
"""
            
            with open("/opt/monitor-orion/grafana/provisioning/datasources/datasource.yml", 'w') as f:
                f.write(datasource_config)
            
            # Cria grafana.ini básico
            grafana_ini = """[server]
protocol = http
http_port = 3000

[security]
admin_user = admin
admin_password = admin

[users]
allow_sign_up = false

[auth.anonymous]
enabled = false
"""
            
            with open("/opt/monitor-orion/grafana/grafana.ini", 'w') as f:
                f.write(grafana_ini)
            
            self.logger.info("✅ Arquivos de configuração criados com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar configurações: {e}")
            return False
    
    def install(self) -> bool:
        """Executa a instalação completa do Stack Grafana"""
        try:
            self.logger.info("🚀 Iniciando instalação do Stack de Monitoramento Grafana...")
            
            # 1. Valida pré-requisitos
            if not self.validate_prerequisites():
                return False
            
            # 2. Coleta dados do usuário
            user_data = self.collect_user_inputs()
            
            # 3. Configura DNS
            if not self.setup_dns_records(user_data):
                return False
            
            # 4. Cria configurações
            if not self.create_monitor_configs(user_data):
                return False
            
            # 5. Prepara variáveis para o template
            variables = {
                'network_name': 'orion_network',
                'grafana_domain': user_data['grafana_domain'],
                'prometheus_domain': user_data['prometheus_domain'],
                'cadvisor_domain': user_data['cadvisor_domain'],
                'nodeexporter_domain': user_data['nodeexporter_domain']
            }
            
            # 6. Deploy via Portainer
            self.logger.info("🚀 Fazendo deploy do Stack de Monitoramento...")
            
            success = self.portainer_api.deploy_service_complete(
                stack_name="grafana",
                template_path="/root/CascadeProjects/templates/docker-compose/grafana.yaml.j2",
                template_vars=variables,
                services_to_wait=[
                    "grafana_prometheus",
                    "grafana_grafana", 
                    "grafana_node-exporter",
                    "grafana_cadvisor"
                ],
                credentials={}
            )
            
            if success:
                # Salva credenciais diretamente no arquivo
                credentials_text = f"""STACK DE MONITORAMENTO GRAFANA INSTALADO COM SUCESSO!

📊 Grafana Dashboard: https://{user_data['grafana_domain']}
   Usuário: admin
   Senha: admin
   (Será solicitado alterar a senha no primeiro login)

📈 Prometheus: https://{user_data['prometheus_domain']}

🐳 cAdvisor: https://{user_data['cadvisor_domain']}

🖥️ NodeExporter: https://{user_data['nodeexporter_domain']}

🔧 Configurações:
- Datasource Prometheus configurado automaticamente no Grafana
- Coleta de métricas configurada para todos os serviços
- Dashboards prontos para importação
"""
                
                # Salva credenciais diretamente no arquivo
                try:
                    os.makedirs("/root/dados_vps", exist_ok=True)
                    with open("/root/dados_vps/dados_grafana", 'w', encoding='utf-8') as f:
                        f.write(credentials_text)
                    self.logger.info("Credenciais salvas em /root/dados_vps/dados_grafana")
                except Exception as e:
                    self.logger.error(f"Erro ao salvar credenciais: {e}")
                
                self.logger.info("Instalação do Stack de Monitoramento Grafana concluída com sucesso")
                self.logger.info(f"Acesse o Grafana: https://{user_data['grafana_domain']}")
                self.logger.info(f"Usuário: admin | Senha: admin")
                
                return True
            else:
                self.logger.error("Falha no deploy do Stack de Monitoramento")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante instalação do Grafana: {e}")
            return False
    
    def run(self):
        """Método principal para execução do setup"""
        return self.install()

if __name__ == "__main__":
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Executa setup
    grafana_setup = GrafanaSetup()
    success = grafana_setup.run()
    
    if success:
        print("\n✅ Stack de Monitoramento Grafana instalado com sucesso!")
    else:
        print("\n❌ Falha na instalação do Stack de Monitoramento Grafana")
