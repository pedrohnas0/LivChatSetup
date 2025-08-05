import requests
import json
import os
import time
import subprocess
import secrets
import string
from typing import Optional, Dict, Any, List
from config import setup_logging

class PortainerAPI:
    """Classe para interagir com a API do Portainer para deploy de stacks"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.base_url = None
        self.token = None
        self.endpoint_id = None
        self.swarm_id = None
        self.credentials_file = "/root/dados_vps/dados_portainer"
    
    def load_credentials(self) -> bool:
        """Carrega credenciais do Portainer do arquivo dados_portainer"""
        try:
            if not os.path.exists(self.credentials_file):
                self.logger.info("Arquivo de credenciais do Portainer não encontrado")
                return self.create_credentials_file()
            
            with open(self.credentials_file, 'r') as f:
                content = f.read()
            
            # Extrai informações do arquivo
            for line in content.split('\n'):
                if line.startswith('Dominio do portainer:'):
                    self.base_url = line.split(':', 1)[1].strip()
                    if not self.base_url.startswith('https://'):
                        self.base_url = f"https://{self.base_url}"
            
            if not self.base_url:
                self.logger.error("URL do Portainer não encontrada no arquivo de credenciais")
                return False
            
            self.logger.info(f"Credenciais carregadas. URL: {self.base_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais: {e}")
            return False
    
    def create_credentials_file(self) -> bool:
        """Cria arquivo de credenciais perguntando interativamente ao usuário"""
        try:
            print("\n" + "="*80)
            print("CONFIGURAÇÃO DAS CREDENCIAIS DO PORTAINER")
            print("="*80)
            print("\nPara fazer deploy das stacks via API do Portainer, precisamos das credenciais.")
            print("\nPasso 1/3")
            portainer_url = input("Digite a URL do Portainer (ex: ptn.dev.livchat.ai): ").strip()
            
            print("\nPasso 2/3")
            username = input("Digite seu Usuário (ex: admin): ").strip()
            
            print("\nPasso 3/3")
            print("Obs: A senha não aparecerá ao digitar")
            import getpass
            password = getpass.getpass("Digite a Senha: ").strip()
            
            if not portainer_url or not username or not password:
                self.logger.error("Todas as credenciais são obrigatórias")
                return False
            
            # Testa as credenciais antes de salvar
            if self.test_credentials(portainer_url, username, password):
                # Salva as credenciais no arquivo
                os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
                
                with open(self.credentials_file, 'w') as f:
                    f.write(f"[ PORTAINER ]\n")
                    f.write(f"Dominio do portainer: {portainer_url}\n\n")
                    f.write(f"Usuario: {username}\n\n")
                    f.write(f"Senha: {password}\n\n")
                    f.write(f"Token: \n")
                
                self.logger.info("Credenciais do Portainer salvas com sucesso")
                return True
            else:
                self.logger.error("Credenciais inválidas. Não foi possível autenticar com o Portainer")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao criar arquivo de credenciais: {e}")
            return False
    
    def test_credentials(self, portainer_url: str, username: str, password: str) -> bool:
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
            
            self.logger.error(f"Falha na autenticação: HTTP {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao testar credenciais: {e}")
            return False
    
    def authenticate(self) -> bool:
        """Autentica com o Portainer e obtém token JWT"""
        try:
            if not self.base_url:
                if not self.load_credentials():
                    return False
            
            # Lê credenciais do arquivo e recarrega base_url
            with open(self.credentials_file, 'r') as f:
                content = f.read()
            
            username = None
            password = None
            
            for line in content.split('\n'):
                if line.startswith('Dominio do portainer:'):
                    self.base_url = line.split(':', 1)[1].strip()
                    if not self.base_url.startswith('https://'):
                        self.base_url = f"https://{self.base_url}"
                elif line.startswith('Usuario:'):
                    username = line.split(':', 1)[1].strip()
                elif line.startswith('Senha:'):
                    password = line.split(':', 1)[1].strip()
            
            if not username or not password:
                self.logger.error("Usuário ou senha não encontrados no arquivo de credenciais")
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
    
    def wait_for_service(self, service_name: str, timeout: int = 300) -> bool:
        """Aguarda serviço ficar online usando docker service ls como o script original"""
        start_time = time.time()
        
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
                
                if result.returncode == 0 and result.stdout.strip():
                    # Verifica se o serviço está 1/1 (running)
                    if "1/1" in result.stdout:
                        self.logger.info(f"🟢 O serviço {service_name} está online")
                        return True
                    else:
                        self.logger.debug(f"Serviço {service_name}: {result.stdout.strip()}")
                        
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout ao verificar status do {service_name}")
            except Exception as e:
                self.logger.warning(f"Erro ao verificar status do {service_name}: {e}")
                
            time.sleep(30)  # Aguarda 30s como o script original
        
        self.logger.error(f"Timeout aguardando {service_name} ficar online")
        return False
    
    def wait_for_multiple_services(self, services: list, timeout: int = 300) -> bool:
        """Aguarda múltiplos serviços ficarem online como o script original"""
        start_time = time.time()
        services_status = {service: "pendente" for service in services}
        
        self.logger.info(f"Aguardando serviços ficarem online: {', '.join(services)}")
        self.logger.info("Este processo pode demorar um pouco. Se levar mais de 5 minutos, algo deu errado.")
        
        while time.time() - start_time < timeout:
            all_active = True
            self.logger.debug(f"Verificando serviços... Tempo decorrido: {int(time.time() - start_time)}s")
            
            for service in services:
                try:
                    self.logger.debug(f"Verificando serviço: {service}")
                    result = subprocess.run(
                        f'docker service ls --filter "name={service}" --format "{{{{.Name}}}} {{{{.Replicas}}}}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    self.logger.debug(f"Resultado para {service}: returncode={result.returncode}, stdout='{result.stdout.strip()}'")
                    
                    if result.returncode == 0 and "1/1" in result.stdout:
                        if services_status[service] != "ativo":
                            self.logger.info(f"🟢 O serviço {service} está online")
                            services_status[service] = "ativo"
                    else:
                        self.logger.debug(f"Serviço {service} não está 1/1: '{result.stdout.strip()}'")
                        if services_status[service] != "pendente":
                            services_status[service] = "pendente"
                        all_active = False
                        
                except Exception as e:
                    self.logger.debug(f"Erro ao verificar {service}: {e}")
                    all_active = False
            
            self.logger.debug(f"Status dos serviços: {services_status}")
            self.logger.debug(f"Todos ativos: {all_active}")
            
            # Sai do loop quando todos os serviços estiverem ativos
            if all_active:
                self.logger.info("Todos os serviços estão online!")
                time.sleep(1)
                return True
                
            self.logger.debug("Aguardando 30s antes da próxima verificação...")
            time.sleep(30)
        
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
        """Salva credenciais do serviço"""
        try:
            credentials_path = f"/root/dados_vps/dados_{service_name}"
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            
            # Salvar credenciais
            with open(credentials_path, 'w', encoding='utf-8') as f:
                for key, value in credentials.items():
                    f.write(f"{key}={value}\n")
            
            self.logger.info(f"Credenciais salvas em {credentials_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {e}")
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
            template_engine = TemplateEngine()
            rendered_content = template_engine.render_template(template_path, template_vars)
            
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
