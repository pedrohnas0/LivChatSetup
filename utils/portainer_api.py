import requests
import json
import os
import time
import subprocess
import secrets
import string
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import setup_logging, POLL_INTERVAL_FAST_SECONDS, LOG_STATUS_INTERVAL_SECONDS, WAIT_TIMEOUT_SECONDS_DEFAULT
from utils.config_manager import ConfigManager

class PortainerAPI:
    """Classe para interagir com a API do Portainer para deploy de stacks"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.base_url = None
        self.username = None
        self.password = None
        self.token = None
        self.endpoint_id = None
        self.swarm_id = None
        self.config = ConfigManager()
    
    def load_credentials(self) -> bool:
        """Carrega credenciais do Portainer do ConfigManager centralizado"""
        try:
            # Verifica se Portainer está instalado e configurado
            if not self.is_portainer_installed():
                self.logger.error("❌ Portainer não está instalado/rodando")
                self.logger.error("🔧 Instale o Portainer primeiro usando o menu principal:")
                self.logger.error("   1. Execute: sudo python3 main.py")
                self.logger.error("   2. Selecione '[04] Instalação do Portainer'")
                self.logger.error("   3. Confirme o acesso após instalação")
                self.logger.error("   4. Execute novamente esta operação")
                return False
            
            # Verifica se Portainer foi confirmado pelo usuário
            portainer_config = self.config.get_app_config("portainer")
            if not portainer_config.get("installed"):
                self.logger.error("❌ Portainer não foi confirmado como acessível")
                self.logger.error("🔧 Execute a instalação do Portainer pelo menu principal primeiro")
                return False
            
            # Verifica se tem credenciais salvas
            portainer_creds = self.config.get_app_credentials("portainer")
            if not portainer_creds or not portainer_creds.get("username") or not portainer_creds.get("password"):
                self.logger.error("❌ Credenciais do Portainer não encontradas no ConfigManager")
                self.logger.error("🔧 Execute a instalação do Portainer pelo menu principal primeiro")
                self.logger.error("   (O processo irá coletar e salvar as credenciais automaticamente)")
                return False
            
            # Carrega configuração e credenciais
            self.base_url = portainer_creds.get("url") or portainer_config.get("url")
            if not self.base_url:
                self.base_url = f"https://{portainer_config.get('domain')}"
            
            if not self.base_url.startswith('https://'):
                self.base_url = f"https://{self.base_url}"
            
            # Salva as credenciais para uso da API
            self.username = portainer_creds.get("username")
            self.password = portainer_creds.get("password")
            
            self.logger.info(f"Portainer encontrado e configurado: {self.base_url}")
            self.logger.info(f"Credenciais carregadas para usuário: {self.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais: {e}")
            return False
    
    def is_portainer_installed(self) -> bool:
        """Verifica se Portainer está instalado e rodando"""
        try:
            # Primeiro verifica no ConfigManager se foi instalado
            portainer_config = self.config.get_app_config("portainer")
            if portainer_config.get("installed") and portainer_config.get("url"):
                # Verifica se está realmente rodando
                result = subprocess.run(
                    "docker stack ls --format '{{.Name}}'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "portainer" in result.stdout:
                    # Já tem URL salva, usa ela
                    self.base_url = portainer_config["url"]
                    self.logger.info(f"Portainer encontrado rodando: {self.base_url}")
                    return True
            
            # Senão, verifica apenas se stack está rodando
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "portainer" in result.stdout
        except Exception:
            return False
    
    
    def create_credentials_file(self) -> bool:
        """Cria arquivo de credenciais perguntando interativamente ao usuário"""
        try:
            print(f"\n🐳 CONFIGURAÇÃO CREDENCIAIS PORTAINER")
            print("─" * 45)
            print("Para fazer deploy das stacks via API do Portainer, precisamos das credenciais.")
            
            # Verifica se já tem URL salva na configuração do Portainer
            portainer_config = self.config.get_app_config("portainer")
            if portainer_config.get("url"):
                suggested_url = portainer_config["url"].replace("https://", "")
            else:
                suggested_url = self.config.suggest_domain("ptn")
            
            print(f"\n📝 Passo 1/3")
            if suggested_url:
                prompt = f"URL do Portainer (Enter para '{suggested_url}' ou digite outra)"
            else:
                prompt = "Digite a URL do Portainer (ex: ptn.seudominio.com)"
            
            portainer_url = input(f"{prompt}: ").strip()
            if not portainer_url and suggested_url:
                portainer_url = suggested_url
            
            print(f"\n👤 Passo 2/3")
            # Sugere email padrão do ConfigManager para autenticação
            default_email = self.config.get_user_email()
            if default_email:
                prompt = f"Usuário do Portainer (Enter para '{default_email}' ou digite outro)"
                username = input(f"{prompt}: ").strip()
                if not username:
                    username = default_email
            else:
                username = input("Usuário do Portainer (Enter para 'admin' ou digite outro): ").strip()
                if not username:
                    username = "admin"
            
            print(f"\n🔐 Passo 3/3")
            # Gera senha segura sugerida
            suggested_password = self.config.generate_secure_password(64)
            print(f"Senha sugerida (64 caracteres seguros): {suggested_password}")
            
            import getpass
            password = getpass.getpass("Digite a senha (Enter para usar a sugerida): ").strip()
            if not password:
                password = suggested_password
            
            if not portainer_url or not username or not password:
                self.logger.error("Todas as credenciais são obrigatórias")
                return False
            
            # Testa as credenciais antes de salvar
            if self.test_credentials(portainer_url, username, password):
                # Salva as credenciais no ConfigManager
                self.config.save_app_credentials("portainer", {
                    "url": portainer_url,
                    "username": username,
                    "password": password
                })
                
                self.logger.info("Credenciais do Portainer salvas com sucesso no ConfigManager")
                return True
            else:
                self.logger.error("Credenciais inválidas. Não foi possível autenticar com o Portainer")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao criar arquivo de credenciais: {e}")
            return False
    
    def test_credentials(self, portainer_url: str, username: str, password: str, silent: bool = False) -> bool:
        """Testa se as credenciais do Portainer são válidas"""
        try:
            base_url = portainer_url
            if not base_url.startswith('https://'):
                base_url = f"https://{base_url}"
            
            response = requests.post(
                f"{base_url}/api/auth",
                json={"username": username, "password": password},
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('jwt')
                if token and token != "null":
                    self.logger.info("Credenciais do Portainer validadas com sucesso")
                    return True
            elif response.status_code == 422:
                # Portainer não inicializado - primeiro acesso
                if not silent:
                    self.logger.error(f"❌ Portainer ainda não foi inicializado!")
                    self.logger.error(f"🔧 AÇÃO NECESSÁRIA:")
                    self.logger.error(f"   1. Acesse: {base_url}")  
                    self.logger.error(f"   2. Crie o usuário administrador")
                    self.logger.error(f"   3. Use o mesmo email/senha que digitou aqui")
                    self.logger.error(f"   4. Execute o sistema novamente")
                return False
            elif response.status_code == 404:
                self.logger.error(f"❌ Portainer não acessível em: {base_url}")
                self.logger.error(f"🔧 Verifique se o Portainer está rodando e acessível")
                return False
            
            self.logger.error(f"Falha na autenticação: HTTP {response.status_code}")
            if response.status_code == 401:
                self.logger.error("❌ Credenciais incorretas. Verifique usuário e senha.")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao testar credenciais: {e}")
            return False
    
    def initialize_portainer(self, base_url: str, username: str, password: str) -> bool:
        """Inicializa Portainer automaticamente criando o usuário admin"""
        try:
            # Primeiro verifica se realmente não está inicializado
            response = requests.get(f"{base_url}/api/status", verify=False, timeout=10)
            if response.status_code != 200:
                return False
            
            status = response.json()
            if not status.get("RequiresInitialConfiguration", False):
                # Já inicializado
                return True
            
            self.logger.info("🔧 Inicializando Portainer automaticamente...")
            
            # Criar usuário admin
            init_data = {
                "Username": username,
                "Password": password
            }
            
            response = requests.post(
                f"{base_url}/api/users/admin/init",
                json=init_data,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info("✅ Usuário admin criado com sucesso")
                # Aguarda um pouco para o Portainer processar
                time.sleep(2)
                return True
            else:
                self.logger.error(f"❌ Falha ao criar usuário admin: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização automática: {e}")
            return False
    
    def authenticate(self) -> bool:
        """Autentica com o Portainer e obtém token JWT"""
        try:
            if not self.base_url:
                if not self.load_credentials():
                    return False
            
            # Carrega credenciais do ConfigManager
            portainer_creds = self.config.get_app_credentials("portainer")
            
            if not portainer_creds:
                self.logger.error("Credenciais do Portainer não encontradas no ConfigManager")
                return False
            
            username = portainer_creds.get("username")
            password = portainer_creds.get("password")
            
            # Atualiza base_url se necessário
            if portainer_creds.get("url"):
                self.base_url = portainer_creds["url"]
                if not self.base_url.startswith('https://'):
                    self.base_url = f"https://{self.base_url}"
            
            if not username or not password:
                self.logger.error("Usuário ou senha não encontrados nas credenciais")
                return False
            
            # Tenta obter token com retry
            max_attempts = 6
            for attempt in range(max_attempts):
                try:
                    response = requests.post(
                        f"{self.base_url}/api/auth",
                        json={"username": username, "password": password},
                        verify=False,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.token = data.get('jwt')
                        
                        if self.token and self.token != "null":
                            self.logger.info(f"Token obtido com sucesso (tentativa {attempt + 1})")
                            return True
                    
                    self.logger.warning(f"Falha na autenticação (tentativa {attempt + 1}/{max_attempts})")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
                        
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Erro de conexão na tentativa {attempt + 1}: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
            
            self.logger.error("Falha ao obter token após todas as tentativas")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro na autenticação: {e}")
            return False
    
    def get_endpoint_id(self) -> bool:
        """Obtém o ID do endpoint primary"""
        try:
            if not self.token:
                if not self.authenticate():
                    return False
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/api/endpoints",
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                endpoints = response.json()
                for endpoint in endpoints:
                    if endpoint.get('Name') == 'primary':
                        self.endpoint_id = endpoint.get('Id')
                        self.logger.info(f"Endpoint ID obtido: {self.endpoint_id}")
                        return True
                
                self.logger.error("Endpoint 'primary' não encontrado")
                return False
            else:
                self.logger.error(f"Erro ao obter endpoints: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao obter endpoint ID: {e}")
            return False
    
    def get_swarm_id(self) -> bool:
        """Obtém o ID do Swarm"""
        try:
            if not self.endpoint_id:
                if not self.get_endpoint_id():
                    return False
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/api/endpoints/{self.endpoint_id}/docker/swarm",
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                swarm_data = response.json()
                self.swarm_id = swarm_data.get('ID')
                self.logger.info(f"Swarm ID obtido: {self.swarm_id}")
                return True
            else:
                self.logger.error(f"Erro ao obter Swarm ID: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao obter Swarm ID: {e}")
            return False
    
    def deploy_stack(self, stack_name: str, stack_file_path: str) -> bool:
        """Faz deploy de uma stack via API do Portainer"""
        try:
            # Verifica se todos os dados necessários estão disponíveis
            if not self.token and not self.authenticate():
                return False
            
            if not self.endpoint_id and not self.get_endpoint_id():
                return False
            
            if not self.swarm_id and not self.get_swarm_id():
                return False
            
            if not os.path.exists(stack_file_path):
                self.logger.error(f"Arquivo de stack não encontrado: {stack_file_path}")
                return False
            
            # Verifica se a stack já existe
            if self.check_stack_exists(stack_name):
                self.logger.info(f"Stack {stack_name} já existe, pulando deploy")
                return True
            
            # Prepara dados para o deploy
            headers = {"Authorization": f"Bearer {self.token}"}
            
            with open(stack_file_path, 'rb') as f:
                files = {'file': (f"{stack_name}.yaml", f, 'application/x-yaml')}
                data = {
                    'Name': stack_name,
                    'SwarmID': self.swarm_id,
                    'endpointId': str(self.endpoint_id)
                }
                
                self.logger.info(f"Fazendo deploy da stack {stack_name}")
                response = requests.post(
                    f"{self.base_url}/api/stacks/create/swarm/file",
                    headers=headers,
                    files=files,
                    data=data,
                    verify=False,
                    timeout=60
                )
            
            if response.status_code == 200:
                response_data = response.json()
                if 'Id' in response_data:
                    self.logger.info(f"Deploy da stack {stack_name} realizado com sucesso")
                    return True
                else:
                    self.logger.error(f"Resposta inesperada do servidor para stack {stack_name}")
                    self.logger.error(f"Resposta: {response_data}")
                    return False
            else:
                self.logger.error(f"Erro no deploy da stack {stack_name}: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    self.logger.error(f"Detalhes do erro: {error_data}")
                except:
                    self.logger.error(f"Resposta do servidor: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no deploy da stack {stack_name}: {e}")
            return False
    
    def check_stack_exists(self, stack_name: str) -> bool:
        """Verifica se uma stack já existe"""
        try:
            if not self.token and not self.authenticate():
                return False
            
            if not self.endpoint_id and not self.get_endpoint_id():
                return False
            
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/api/stacks",
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                stacks = response.json()
                for stack in stacks:
                    if stack.get('Name') == stack_name:
                        return True
                return False
            else:
                self.logger.error(f"Erro ao verificar stacks existentes: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar se stack existe: {e}")
            return False
    
    # =====================================================
    # MÉTODOS GENÉRICOS PARA DEPLOY DE SERVIÇOS
    # =====================================================
    
    def create_volumes(self, volumes: List[str]) -> bool:
        """Cria volumes Docker necessários"""
        for volume in volumes:
            try:
                result = subprocess.run(
                    f"docker volume create {volume}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.logger.info(f"Volume {volume} criado com sucesso")
                else:
                    self.logger.warning(f"Volume {volume} já existe ou erro na criação")
            except Exception as e:
                self.logger.error(f"Erro ao criar volume {volume}: {e}")
                return False
        return True
    
    def wait_for_service(self, service_name: str, timeout: int = WAIT_TIMEOUT_SECONDS_DEFAULT) -> bool:
        """Aguarda serviço ficar online com polling rápido e logs periódicos."""
        start_time = time.time()
        last_log_time = start_time

        self.logger.info(f"Aguardando {service_name} ficar online (timeout: {timeout}s)")
        self.logger.info("Este processo pode demorar um pouco. Se levar mais de 5 minutos, algo deu errado.")

        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    f'docker service ls --filter "name={service_name}" --format "{{{{.Name}}}} {{{{.Replicas}}}}"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                out = result.stdout.strip()
                if result.returncode == 0 and out:
                    if "1/1" in out:
                        self.logger.info(f"🟢 O serviço {service_name} está online")
                        return True

                # Logs periódicos a cada LOG_STATUS_INTERVAL_SECONDS
                now = time.time()
                if now - last_log_time >= LOG_STATUS_INTERVAL_SECONDS:
                    status = out or "indisponível"
                    self.logger.info(f"Aguardando {service_name}... status atual: {status}")
                    last_log_time = now

            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout ao verificar status do {service_name}")
            except Exception as e:
                self.logger.warning(f"Erro ao verificar status do {service_name}: {e}")

            time.sleep(POLL_INTERVAL_FAST_SECONDS)

        self.logger.error(f"Timeout aguardando {service_name} ficar online")
        return False
    
    def wait_for_multiple_services(self, services: list, timeout: int = WAIT_TIMEOUT_SECONDS_DEFAULT) -> bool:
        """Aguarda múltiplos serviços com polling rápido e logs periódicos."""
        start_time = time.time()
        last_log_time = start_time
        services_status = {service: "pendente" for service in services}

        self.logger.info(f"Aguardando serviços ficarem online: {', '.join(services)}")
        self.logger.info("Este processo pode demorar um pouco. Se levar mais de 5 minutos, algo deu errado.")

        while time.time() - start_time < timeout:
            all_active = True

            for service in services:
                try:
                    result = subprocess.run(
                        f'docker service ls --filter "name={service}" --format "{{{{.Name}}}} {{{{.Replicas}}}}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    out = result.stdout.strip()
                    if result.returncode == 0 and "1/1" in out:
                        if services_status[service] != "ativo":
                            self.logger.info(f"🟢 O serviço {service} está online")
                            services_status[service] = "ativo"
                    else:
                        if services_status[service] != "pendente":
                            services_status[service] = "pendente"
                        all_active = False

                except Exception as e:
                    self.logger.debug(f"Erro ao verificar {service}: {e}")
                    all_active = False

            # Logs periódicos agregados a cada LOG_STATUS_INTERVAL_SECONDS
            now = time.time()
            if now - last_log_time >= LOG_STATUS_INTERVAL_SECONDS:
                pendentes = [s for s, st in services_status.items() if st != "ativo"]
                if pendentes:
                    self.logger.info(f"Aguardando serviços: {', '.join(pendentes)}")
                last_log_time = now

            if all_active:
                self.logger.info("Todos os serviços estão online!")
                time.sleep(1)
                return True

            time.sleep(POLL_INTERVAL_FAST_SECONDS)

        self.logger.error(f"Timeout aguardando serviços ficarem online")
        return False
    
    def verify_stack_running(self, stack_name: str) -> bool:
        """Verifica se a stack está rodando"""
        try:
            result = subprocess.run(
                "docker stack ls --format '{{.Name}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                stacks = result.stdout.strip().split('\n')
                if stack_name in stacks:
                    self.logger.info(f"Stack do {stack_name} encontrada")
                    return True
            
            self.logger.error(f"Stack do {stack_name} não encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar stack {stack_name}: {e}")
            return False
    
    def save_service_credentials(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """Salva credenciais do serviço no ConfigManager centralizado"""
        try:
            # Adiciona timestamp
            credentials["configured_at"] = datetime.now().isoformat()
            
            # Salva no ConfigManager
            self.config.save_app_credentials(service_name, credentials)
            
            self.logger.info(f"Credenciais de {service_name} salvas no ConfigManager centralizado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais de {service_name}: {e}")
            return False
    
    def generate_password(self, length: int = 16, use_special_chars: bool = True) -> str:
        """Gera senha aleatória"""
        if use_special_chars:
            chars = string.ascii_letters + string.digits + '_@#$'
        else:
            chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def generate_hex_key(self, length: int = 16) -> str:
        """Gera chave hexadecimal"""
        return secrets.token_hex(length)
    
    def deploy_service_complete(self, 
                             service_name: str, 
                             template_path: str, 
                             template_vars: Dict[str, Any],
                             volumes: List[str] = None,
                             wait_service: str = None,
                             wait_services: List[str] = None,
                             credentials: Dict[str, Any] = None) -> bool:
        """Deploy completo de um serviço com todas as etapas"""
        try:
            from utils.template_engine import TemplateEngine
            
            # 1. Criar volumes se necessário
            if volumes:
                if not self.create_volumes(volumes):
                    return False
            
            # 2. Renderizar template
            self.logger.debug(f"🔧 Iniciando renderização do template: {template_path}")
            self.logger.debug(f"🔧 Variáveis do template: {template_vars}")
            
            template_engine = TemplateEngine()
            rendered_content = template_engine.render_template(template_path, template_vars)
            
            if not rendered_content:
                self.logger.error(f"❌ Falha na renderização do template: {template_path}")
                self.logger.error(f"❌ Template engine retornou conteúdo vazio")
                return False
            
            self.logger.debug(f"✅ Template renderizado com sucesso. Tamanho: {len(rendered_content)} chars")
            
            # 3. Salvar stack temporária
            stack_path = f"/tmp/{service_name}_stack.yaml"
            with open(stack_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
            
            self.logger.info(f"Stack do {service_name} criada com sucesso")
            
            # 4. Deploy via API Portainer
            if not self.deploy_stack(service_name, stack_path):
                return False
            
            # 5. Aguardar serviço(s) se especificado
            if wait_services:
                if not self.wait_for_multiple_services(wait_services):
                    return False
            elif wait_service:
                if not self.wait_for_service(wait_service):
                    return False
            
            # 6. Verificar stack
            if not self.verify_stack_running(service_name):
                return False
            
            # 7. Salvar credenciais se fornecidas
            if credentials:
                if not self.save_service_credentials(service_name, credentials):
                    return False
            
            self.logger.info(f"Deploy completo do {service_name} realizado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante deploy completo do {service_name}: {e}")
            return False
