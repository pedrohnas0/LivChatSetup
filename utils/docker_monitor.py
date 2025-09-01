#!/usr/bin/env python3
"""
Monitor de Serviços Docker - Sistema otimizado de coleta de métricas
"""

import subprocess
import json
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

class DockerMonitor:
    """Monitor eficiente de serviços Docker com cache e thread assíncrona"""
    
    def __init__(self, update_interval: float = 2.0):
        """
        Inicializa o monitor
        Args:
            update_interval: Intervalo em segundos entre atualizações (padrão 2s)
        """
        self.logger = logging.getLogger(__name__)
        self.update_interval = update_interval
        
        # Cache de dados
        self.services_cache = {}  # Cache de serviços
        self.stats_cache = {}     # Cache de estatísticas
        self.last_update = {}     # Timestamp das últimas atualizações
        
        # Thread de monitoramento
        self.monitoring = False
        self.monitor_thread = None
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        # Mapeamento de nomes de serviços para IDs simplificados
        self.service_mapping = {
            'traefik': ['traefik'],
            'portainer': ['portainer', 'portainer-agent'],
            'redis': ['redis'],
            'postgres': ['postgres', 'postgresql'],
            'pgvector': ['pgvector'],
            'minio': ['minio'],
            'chatwoot': ['chatwoot', 'chatwoot-web', 'chatwoot-worker'],
            'directus': ['directus'],
            'n8n': ['n8n'],
            'grafana': ['grafana', 'prometheus', 'loki'],
            'gowa': ['gowa'],
            'passbolt': ['passbolt'],
            'evolution': ['evolution', 'evolution-api'],
            'livchatbridge': ['livchatbridge']
        }
        
    def start_monitoring(self):
        """Inicia o monitoramento assíncrono"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.debug("Monitoramento Docker iniciado")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.logger.debug("Monitoramento Docker parado")
    
    def _monitor_loop(self):
        """Loop principal de monitoramento (executa em thread separada)"""
        while self.monitoring:
            try:
                # Atualizar lista de serviços
                self._update_services()
                
                # Atualizar estatísticas
                self._update_stats()
                
                # Aguardar próximo ciclo
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(5)  # Espera maior em caso de erro
    
    def _update_services(self):
        """Atualiza lista de serviços Docker"""
        try:
            # Comando otimizado para obter serviços
            cmd = [
                'docker', 'service', 'ls',
                '--format', '{{json .}}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                services = {}
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            service = json.loads(line)
                            # Extrair informações relevantes
                            service_name = service.get('Name', '')
                            service_id = self._get_service_id(service_name)
                            
                            if service_id:
                                replicas = service.get('Replicas', '0/0')
                                mode = service.get('Mode', '')
                                
                                services[service_id] = {
                                    'name': service_name,
                                    'replicas': replicas,
                                    'mode': mode,
                                    'running': self._parse_replicas(replicas)
                                }
                        except json.JSONDecodeError:
                            continue
                
                # Atualizar cache com lock
                with self.lock:
                    self.services_cache = services
                    self.last_update['services'] = datetime.now()
                    
        except subprocess.TimeoutExpired:
            self.logger.warning("Timeout ao obter lista de serviços")
        except Exception as e:
            self.logger.error(f"Erro ao atualizar serviços: {e}")
    
    def _update_stats(self):
        """Atualiza estatísticas de containers"""
        try:
            # Comando otimizado para obter stats sem stream
            cmd = [
                'docker', 'stats', '--no-stream', '--no-trunc',
                '--format', '{{json .}}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                stats = {}
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            stat = json.loads(line)
                            container_name = stat.get('Name', '')
                            
                            # Mapear container para serviço
                            service_id = self._container_to_service(container_name)
                            
                            if service_id:
                                # Parsear CPU e Memória
                                cpu_percent = self._parse_cpu(stat.get('CPUPerc', '0%'))
                                mem_usage = self._parse_memory(stat.get('MemUsage', '0B / 0B'))
                                
                                if service_id not in stats:
                                    stats[service_id] = {
                                        'cpu': 0.0,
                                        'mem': 0,
                                        'containers': 0
                                    }
                                
                                # Acumular estatísticas (para múltiplos containers)
                                stats[service_id]['cpu'] += cpu_percent
                                stats[service_id]['mem'] += mem_usage
                                stats[service_id]['containers'] += 1
                        except json.JSONDecodeError:
                            continue
                
                # Calcular médias para serviços com múltiplos containers
                for service_id in stats:
                    if stats[service_id]['containers'] > 1:
                        stats[service_id]['cpu'] /= stats[service_id]['containers']
                
                # Atualizar cache com lock
                with self.lock:
                    self.stats_cache = stats
                    self.last_update['stats'] = datetime.now()
                    
        except subprocess.TimeoutExpired:
            self.logger.warning("Timeout ao obter estatísticas")
        except Exception as e:
            self.logger.error(f"Erro ao atualizar estatísticas: {e}")
    
    def get_service_status(self, service_id: str) -> Dict:
        """
        Obtém status de um serviço específico
        Args:
            service_id: ID do serviço (ex: 'traefik', 'portainer')
        Returns:
            Dict com status do serviço
        """
        with self.lock:
            service_info = self.services_cache.get(service_id, {})
            stats_info = self.stats_cache.get(service_id, {})
            
            # Determinar status
            if not service_info:
                status = None  # Não instalado
            elif service_info.get('running', False):
                status = 'running'
            else:
                status = 'stopped'
            
            return {
                'status': status,
                'replicas': service_info.get('replicas'),
                'cpu': stats_info.get('cpu'),
                'mem': stats_info.get('mem')
            }
    
    def get_all_services(self) -> Dict:
        """
        Obtém status de todos os serviços
        Returns:
            Dict com status de todos os serviços
        """
        all_services = {}
        
        # Lista de todos os serviços possíveis
        for service_id in self.service_mapping.keys():
            all_services[service_id] = self.get_service_status(service_id)
        
        return all_services
    
    def _get_service_id(self, service_name: str) -> Optional[str]:
        """Mapeia nome do serviço Docker para ID simplificado"""
        service_name_lower = service_name.lower()
        
        for service_id, patterns in self.service_mapping.items():
            for pattern in patterns:
                if pattern in service_name_lower:
                    return service_id
        
        return None
    
    def _container_to_service(self, container_name: str) -> Optional[str]:
        """Mapeia nome do container para ID do serviço"""
        container_lower = container_name.lower()
        
        # Primeiro tenta match direto
        for service_id, patterns in self.service_mapping.items():
            for pattern in patterns:
                if pattern in container_lower:
                    return service_id
        
        # Se não encontrar, tenta pelo prefixo do stack
        if '_' in container_name:
            stack_name = container_name.split('_')[0]
            return self._get_service_id(stack_name)
        
        return None
    
    def _parse_replicas(self, replicas_str: str) -> bool:
        """
        Parseia string de réplicas para determinar se está rodando
        Ex: "1/1" -> True, "0/1" -> False
        """
        try:
            if '/' in replicas_str:
                current, desired = replicas_str.split('/')
                return int(current) > 0
        except:
            pass
        return False
    
    def _parse_cpu(self, cpu_str: str) -> float:
        """Parseia string de CPU para float"""
        try:
            return float(cpu_str.replace('%', ''))
        except:
            return 0.0
    
    def _parse_memory(self, mem_str: str) -> int:
        """
        Parseia string de memória para MB
        Ex: "245MiB / 1.5GiB" -> 245
        """
        try:
            if '/' in mem_str:
                used, _ = mem_str.split('/')
                used = used.strip()
                
                # Converter para MB
                if 'GiB' in used or 'GB' in used:
                    value = float(used.replace('GiB', '').replace('GB', '').strip())
                    return int(value * 1024)
                elif 'MiB' in used or 'MB' in used:
                    value = float(used.replace('MiB', '').replace('MB', '').strip())
                    return int(value)
                elif 'KiB' in used or 'KB' in used:
                    value = float(used.replace('KiB', '').replace('KB', '').strip())
                    return int(value / 1024)
                elif 'B' in used:
                    value = float(used.replace('B', '').strip())
                    return int(value / (1024 * 1024))
        except:
            pass
        return 0
    
    def is_docker_available(self) -> bool:
        """Verifica se Docker está disponível"""
        try:
            result = subprocess.run(
                ['docker', 'version'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def is_swarm_active(self) -> bool:
        """Verifica se Docker Swarm está ativo"""
        try:
            result = subprocess.run(
                ['docker', 'info', '--format', '{{.Swarm.LocalNodeState}}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0 and 'active' in result.stdout.lower()
        except:
            return False


# Singleton global para uso em toda aplicação
_monitor_instance = None

def get_monitor() -> DockerMonitor:
    """Obtém instância singleton do monitor"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = DockerMonitor()
    return _monitor_instance


if __name__ == "__main__":
    # Teste do monitor
    import json
    
    logging.basicConfig(level=logging.DEBUG)
    
    monitor = DockerMonitor(update_interval=1.0)
    
    print("Verificando Docker...")
    if not monitor.is_docker_available():
        print("Docker não está disponível!")
        exit(1)
    
    print("Verificando Swarm...")
    if not monitor.is_swarm_active():
        print("Docker Swarm não está ativo!")
        exit(1)
    
    print("Iniciando monitoramento...")
    monitor.start_monitoring()
    
    # Aguardar coleta inicial
    time.sleep(3)
    
    # Exibir status
    print("\n=== Status dos Serviços ===")
    services = monitor.get_all_services()
    
    for service_id, info in services.items():
        status = info['status'] or 'not installed'
        replicas = info['replicas'] or '-'
        cpu = f"{info['cpu']:.1f}%" if info['cpu'] else '-'
        mem = f"{info['mem']}M" if info['mem'] else '-'
        
        print(f"{service_id:15} Status: {status:12} Replicas: {replicas:6} CPU: {cpu:7} MEM: {mem:7}")
    
    print("\nMonitorando por 10 segundos...")
    time.sleep(10)
    
    monitor.stop_monitoring()
    print("Monitoramento finalizado.")