#!/usr/bin/env python3
"""
Template Engine para processar templates Jinja2
"""

import os
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template

class TemplateEngine:
    """Engine para processar templates Jinja2"""
    
    def __init__(self, templates_dir: str = "/root/CascadeProjects/LivChatSetup/templates"):
        self.templates_dir = templates_dir
        self.logger = logging.getLogger(__name__)
        
        # Configura ambiente Jinja2
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_template(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Renderiza um template com as variáveis fornecidas
        
        Args:
            template_path: Caminho relativo ao template (ex: 'docker-compose/traefik.yaml.j2')
            variables: Dicionário com variáveis para substituição
            
        Returns:
            String com o template renderizado
        """
        try:
            self.logger.debug(f"🔧 Tentando renderizar template: {template_path}")
            self.logger.debug(f"🔧 Diretório de templates: {self.templates_dir}")
            self.logger.debug(f"🔧 Template path completo: {os.path.join(self.templates_dir, template_path)}")
            
            # Verificar se o arquivo existe
            full_path = os.path.join(self.templates_dir, template_path)
            if not os.path.exists(full_path):
                self.logger.error(f"❌ Template não encontrado: {full_path}")
                return ""
            
            self.logger.debug(f"✅ Template encontrado: {full_path}")
            
            template = self.env.get_template(template_path)
            rendered = template.render(**variables)
            
            self.logger.debug(f"✅ Template {template_path} renderizado com sucesso. Tamanho: {len(rendered)} chars")
            return rendered
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao renderizar template {template_path}: {e}")
            self.logger.error(f"❌ Tipo do erro: {type(e).__name__}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return ""
    
    def render_to_file(self, template_path: str, variables: Dict[str, Any], output_path: str) -> bool:
        """
        Renderiza um template e salva em arquivo
        
        Args:
            template_path: Caminho relativo ao template
            variables: Dicionário com variáveis para substituição
            output_path: Caminho onde salvar o arquivo renderizado
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            rendered_content = self.render_template(template_path, variables)
            
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
            
            self.logger.info(f"Template renderizado salvo em: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar template renderizado: {e}")
            return False
    
    def validate_template(self, template_path: str) -> bool:
        """
        Valida se um template existe e é válido
        
        Args:
            template_path: Caminho relativo ao template
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            self.env.get_template(template_path)
            return True
        except Exception as e:
            self.logger.error(f"Template {template_path} inválido: {e}")
            return False
    
    def list_templates(self, subdirectory: str = "") -> list:
        """
        Lista templates disponíveis
        
        Args:
            subdirectory: Subdiretório para filtrar (ex: 'docker-compose')
            
        Returns:
            Lista de templates disponíveis
        """
        try:
            templates = []
            search_path = os.path.join(self.templates_dir, subdirectory)
            
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith('.j2'):
                            rel_path = os.path.relpath(
                                os.path.join(root, file), 
                                self.templates_dir
                            )
                            templates.append(rel_path)
            
            return sorted(templates)
            
        except Exception as e:
            self.logger.error(f"Erro ao listar templates: {e}")
            return []

def main():
    """Função principal para teste"""
    import sys
    
    # Configura logging básico
    logging.basicConfig(level=logging.DEBUG)
    
    engine = TemplateEngine()
    
    # Lista templates disponíveis
    templates = engine.list_templates()
    print("Templates disponíveis:")
    for template in templates:
        print(f"  - {template}")
    
    # Teste de renderização se template fornecido
    if len(sys.argv) > 1:
        template_path = sys.argv[1]
        variables = {
            'network_name': 'test_network',
            'email': 'test@example.com',
            'domain': 'test.example.com'
        }
        
        try:
            result = engine.render_template(template_path, variables)
            print(f"\nTemplate {template_path} renderizado:")
            print("-" * 50)
            print(result)
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    main()
