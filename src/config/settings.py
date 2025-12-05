"""
Gerenciador de configurações.
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml
from dotenv import load_dotenv
from loguru import logger


class SettingsManager:
    """Gerencia configurações do aplicativo."""

    def __init__(self, config_path: str = "config/default_config.yaml"):
        """
        Inicializa gerenciador de configurações.
        
        Args:
            config_path: Caminho do arquivo de configuração YAML
        """
        # Carregar variáveis de ambiente
        env_path = Path("config/.env")
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Variáveis de ambiente carregadas de {env_path}")
        else:
            logger.warning(f"Arquivo .env não encontrado em {env_path}")

        # Carregar configuração YAML
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        logger.info(f"Configurações carregadas de {config_path}")

    def _load_config(self) -> dict:
        """Carrega configuração do arquivo YAML."""
        if not self.config_path.exists():
            logger.error(f"Arquivo de configuração não encontrado: {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém valor de configuração usando notação de ponto.
        
        Args:
            key: Chave no formato 'section.subsection.key'
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração ou default
            
        Example:
            >>> settings.get('ocr.languages')
            ['en', 'ko']
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Define valor de configuração usando notação de ponto.
        
        Args:
            key: Chave no formato 'section.subsection.key'
            value: Valor a definir
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        logger.debug(f"Configuração atualizada: {key} = {value}")

    def save(self):
        """Salva configurações no arquivo YAML."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
            logger.info(f"Configurações salvas em {self.config_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")

    def get_cache_db_path(self) -> Path:
        """Retorna caminho do banco de cache."""
        db_path = self.get('cache.db_path', './cache/translations.db')
        return Path(db_path)

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Obtém API key do ambiente.
        
        Args:
            provider: Nome do provedor ('groq', 'claude', 'deepseek')
            
        Returns:
            API key ou None se não encontrada
        """
        key_map = {
            'groq': 'GROQ_API_KEY',
            'claude': 'CLAUDE_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY'
        }
        
        env_var = key_map.get(provider.lower())
        if env_var:
            key = os.getenv(env_var)
            if key and len(key) > 10:  # Validação básica
                return key
            logger.debug(f"API key '{env_var}' não configurada ou inválida")
        
        return None
