"""
Sistema de Tradução Modular com 3 Provedores Gratuitos.

Provedores suportados:
1. Groq API - LLM gratuito (llama-3.3-70b)
2. Google Translate - Via deep-translator
3. Ollama - LLM local (requer instalação)

Arquitetura: Strategy Pattern com fallback automático
"""

from typing import Optional
from abc import ABC, abstractmethod
from loguru import logger

from src.utils.types import TranslationResult, TranslationProvider


# ============================================================================
# CLASSE BASE
# ============================================================================

class TranslatorBase(ABC):
    """Classe abstrata para todos os tradutores."""

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Traduz texto.
        
        Args:
            text: Texto a traduzir
            source_lang: Idioma de origem ('en', 'ko', 'pt')
            target_lang: Idioma de destino ('en', 'ko', 'pt')
            
        Returns:
            Texto traduzido ou None em caso de erro
        """
        pass


# ============================================================================
# PROVEDOR 1: GROQ API (GRATUITO - RECOMENDADO)
# ============================================================================

class GroqTranslator(TranslatorBase):
    """
    Tradutor usando Groq API.
    
    Vantagens:
    - Completamente gratuito
    - Muito rápido (~500ms)
    - Limite: 6.000 req/min
    - Modelo: llama-3.3-70b
    
    Obter chave: https://console.groq.com
    """

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        """
        Inicializa tradutor Groq.
        
        Args:
            api_key: Chave API (formato: gsk_...)
            model: Modelo a usar (llama-3.3-70b-versatile, llama-3.1-8b-instant)
        """
        if not api_key or not api_key.startswith('gsk_'):
            raise ValueError("API key inválida. Formato esperado: gsk_...")
        
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        
        logger.info(f"✓ GroqTranslator inicializado - modelo: {model}")

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Traduz usando Groq API."""
        try:
            import requests

            # Mapear códigos para nomes completos
            lang_names = {
                'en': 'English',
                'ko': 'Korean',
                'pt': 'Portuguese',
                'ja': 'Japanese',
                'zh': 'Chinese'
            }
            
            source_name = lang_names.get(source_lang, source_lang)
            target_name = lang_names.get(target_lang, target_lang)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a professional translator. Translate from {source_name} to {target_name}. Return ONLY the translation, no explanations or extra text."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500,
                "top_p": 1,
                "stream": False
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                translated = data['choices'][0]['message']['content'].strip()
                
                # Remover aspas extras se houver
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1]
                
                logger.debug(f"Groq: '{text[:30]}...' → '{translated[:30]}...'")
                return translated
                
            elif response.status_code == 429:
                logger.warning("Groq: Limite de taxa excedido")
                return None
            else:
                # Log detalhado do erro
                error_details = response.text if response.text else "Sem detalhes"
                logger.error(f"Groq: HTTP {response.status_code} - {error_details}")
                return None

        except requests.Timeout:
            logger.error("Groq: Timeout (>15s)")
            return None
        except Exception as e:
            logger.error(f"Groq: Erro - {e}")
            return None


# ============================================================================
# PROVEDOR 2: GOOGLE TRANSLATE (GRATUITO)
# ============================================================================

class GoogleTranslator(TranslatorBase):
    """
    Tradutor usando Google Translate.
    
    Vantagens:
    - Completamente gratuito
    - Não requer API key
    - Confiável e rápido
    - 100+ idiomas suportados
    
    Usa biblioteca: deep-translator
    """

    def __init__(self):
        """Inicializa tradutor Google."""
        try:
            from deep_translator import GoogleTranslator as GT
            self.translator_class = GT
            logger.info("✓ GoogleTranslator inicializado (deep-translator)")
        except ImportError:
            logger.error("deep-translator não instalado. Execute: pip install deep-translator")
            raise

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Traduz usando Google Translate."""
        try:
            # deep-translator usa 'auto' para detecção automática
            source = source_lang if source_lang != 'unknown' else 'auto'
            
            translator = self.translator_class(source=source, target=target_lang)
            translated = translator.translate(text)
            
            if translated and translated != text:
                logger.debug(f"Google: '{text[:30]}...' → '{translated[:30]}...'")
                return translated
            
            return None

        except Exception as e:
            logger.error(f"Google: Erro - {e}")
            return None


# ============================================================================
# PROVEDOR 3: OLLAMA (LOCAL - GRATUITO)
# ============================================================================

class OllamaTranslator(TranslatorBase):
    """
    Tradutor usando Ollama (LLM local).
    
    Vantagens:
    - 100% local (privacidade total)
    - Sem limites de uso
    - Gratuito
    
    Requer:
    - Instalação: https://ollama.ai
    - Modelo baixado: ollama pull llama3.1
    - Servidor rodando: ollama serve
    """

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        """
        Inicializa tradutor Ollama.
        
        Args:
            model: Modelo a usar (llama3.1, mistral, etc)
            base_url: URL do servidor Ollama
        """
        self.model = model
        self.base_url = base_url
        
        # Testar conexão
        try:
            import requests
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info(f"✓ OllamaTranslator inicializado - modelo: {model}")
            else:
                logger.warning(f"Ollama: Servidor não responde (status {response.status_code})")
        except Exception as e:
            logger.warning(f"Ollama: Não conectado - {e}")

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Traduz usando Ollama local."""
        try:
            import requests

            lang_names = {
                'en': 'English',
                'ko': 'Korean',
                'pt': 'Portuguese',
                'ja': 'Japanese'
            }
            
            target_name = lang_names.get(target_lang, target_lang)

            payload = {
                "model": self.model,
                "prompt": f"Translate the following text to {target_name}. Return only the translation:\n\n{text}",
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 500
                }
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                translated = data.get('response', '').strip()
                
                if translated:
                    logger.debug(f"Ollama: '{text[:30]}...' → '{translated[:30]}...'")
                    return translated
            
            return None

        except requests.Timeout:
            logger.error("Ollama: Timeout (>30s)")
            return None
        except Exception as e:
            logger.error(f"Ollama: Erro - {e}")
            return None


# ============================================================================
# TRADUTOR OFFLINE (FALLBACK)
# ============================================================================

class OfflineTranslator(TranslatorBase):
    """
    Tradutor offline com dicionário básico.
    
    Usado como último recurso quando todos os outros falham.
    """

    def __init__(self):
        """Inicializa dicionário offline básico."""
        self.dictionary = {
            # Inglês → Português
            'hello': 'olá',
            'world': 'mundo',
            'thank you': 'obrigado',
            'thanks': 'obrigado',
            'yes': 'sim',
            'no': 'não',
            'please': 'por favor',
            'sorry': 'desculpe',
            'good': 'bom',
            'bad': 'ruim',
            'morning': 'manhã',
            'night': 'noite',
            'day': 'dia',
            'time': 'tempo',
            'today': 'hoje',
            'tomorrow': 'amanhã',
            'yesterday': 'ontem'
        }
        logger.info("✓ OfflineTranslator inicializado (dicionário básico)")

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Tradução offline básica via dicionário."""
        text_lower = text.lower().strip()
        
        # Busca exata
        if text_lower in self.dictionary:
            translated = self.dictionary[text_lower]
            logger.debug(f"Offline: '{text}' → '{translated}'")
            return translated
        
        # Busca parcial
        for key, value in self.dictionary.items():
            if key in text_lower:
                translated = text_lower.replace(key, value)
                logger.debug(f"Offline: '{text}' → '{translated}' (parcial)")
                return translated
        
        # Sem tradução
        logger.warning(f"Offline: Sem tradução para '{text}'")
        return text  # Retorna original


# ============================================================================
# SERVIÇO DE TRADUÇÃO (ORQUESTRADOR)
# ============================================================================

class TranslationService:
    """
    Orquestrador de tradução com fallback automático.
    
    Tenta tradutores na ordem:
    1. Groq (se configurado)
    2. Google Translate
    3. Ollama (se habilitado)
    4. Offline (fallback final)
    """

    def __init__(
        self,
        groq_key: Optional[str] = None,
        google_enabled: bool = True,
        ollama_enabled: bool = False,
        groq_model: str = "llama-3.3-70b-versatile",
        ollama_model: str = "llama3.1",
        ollama_url: str = "http://localhost:11434"
    ):
        """
        Inicializa serviço de tradução.
        
        Args:
            groq_key: Chave API Groq (obter em console.groq.com)
            google_enabled: Habilitar Google Translate
            ollama_enabled: Habilitar Ollama (requer instalação local)
            groq_model: Modelo Groq a usar
            ollama_model: Modelo Ollama a usar
            ollama_url: URL do servidor Ollama
        """
        self.translators = []

        # 1. Groq (prioridade máxima se configurado)
        if groq_key:
            try:
                translator = GroqTranslator(groq_key, groq_model)
                self.translators.append(('groq', translator))
            except Exception as e:
                logger.warning(f"Groq não inicializado: {e}")

        # 2. Google Translate (sempre habilitado se disponível)
        if google_enabled:
            try:
                translator = GoogleTranslator()
                self.translators.append(('google', translator))
            except Exception as e:
                logger.warning(f"Google não inicializado: {e}")

        # 3. Ollama (se habilitado explicitamente)
        if ollama_enabled:
            try:
                translator = OllamaTranslator(ollama_model, ollama_url)
                self.translators.append(('ollama', translator))
            except Exception as e:
                logger.warning(f"Ollama não inicializado: {e}")

        # 4. Fallback offline (sempre presente)
        self.translators.append(('offline', OfflineTranslator()))

        # Log dos tradutores ativos
        logger.info(f"TranslationService: {len(self.translators)} tradutor(es) ativo(s)")
        for name, _ in self.translators:
            logger.info(f"  → {name}")

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "pt"
    ) -> TranslationResult:
        """
        Traduz texto com fallback automático.
        
        Tenta cada tradutor em ordem até obter sucesso.
        
        Args:
            text: Texto a traduzir
            source_lang: Idioma de origem
            target_lang: Idioma de destino
            
        Returns:
            TranslationResult com texto traduzido e metadados
        """
        if not text or len(text.strip()) == 0:
            return TranslationResult(
                original_text=text,
                translated_text="",
                source_language=source_lang,
                target_language=target_lang,
                provider=TranslationProvider.OFFLINE,
                confidence=0.0
            )

        # Tentar cada tradutor
        for provider_name, translator in self.translators:
            try:
                translated = translator.translate(text, source_lang, target_lang)
                
                if translated and translated != text and len(translated.strip()) > 0:
                    return TranslationResult(
                        original_text=text,
                        translated_text=translated,
                        source_language=source_lang,
                        target_language=target_lang,
                        provider=TranslationProvider(provider_name),
                        confidence=1.0 if provider_name != 'offline' else 0.5
                    )
                    
            except Exception as e:
                logger.warning(f"Falha no tradutor '{provider_name}': {e}")
                continue

        # Se todos falharam, retornar original
        logger.error(f"Nenhum tradutor conseguiu traduzir: '{text}'")
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language=source_lang,
            target_language=target_lang,
            provider=TranslationProvider.OFFLINE,
            confidence=0.0
        )

    def get_active_providers(self) -> list:
        """Retorna lista de provedores ativos."""
        return [name for name, _ in self.translators]

    def test_all_providers(self) -> dict:
        """
        Testa todos os provedores com uma frase simples.
        
        Returns:
            Dict com status de cada provedor
        """
        test_text = "Hello world"
        results = {}

        for provider_name, translator in self.translators:
            try:
                translated = translator.translate(test_text, "en", "pt")
                results[provider_name] = {
                    'status': 'ok' if translated else 'failed',
                    'translation': translated
                }
            except Exception as e:
                results[provider_name] = {
                    'status': 'error',
                    'error': str(e)
                }

        return results
