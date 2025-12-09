"""
Sistema de Tradução Modular com 3 Provedores Gratuitos.

Provedores suportados:

1. Groq API - LLM gratuito (llama-3.3-70b)
2. Google Translate - Via deep-translator
3. Ollama - LLM local (requer instalação)

Arquitetura: Strategy Pattern com fallback automático.
Inclui pós-processamento de glossário para consistência de termos em PT-BR.
"""

from typing import Optional
from abc import ABC, abstractmethod
from pathlib import Path
import re
import time  # Fase 7 – medir tempo de tradução

from loguru import logger

from src.utils.types import TranslationResult, TranslationProvider


# ============================================================================
# CLASSE BASE
# ============================================================================


class TranslatorBase(ABC):
    """Classe abstrata para todos os tradutores."""

    @abstractmethod
    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
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
# GLOSSÁRIO (PÓS-PROCESSAMENTO)
# ============================================================================


class GlossaryPostProcessor:
    """
    Aplica um glossário externo (config/glossary.yaml) ao texto traduzido.

    Estrutura esperada do YAML:

    replace_exact:
      "senpai": "senpai"
      "onee-chan": "irmã mais velha"

    replace_substring:
      "Hero Party": "Equipe do Herói"
      "Guild": "Guilda"
    """

    def __init__(self, path: Optional[Path] = None):
        # Caminho padrão: <repo>/src/config/glossary.yaml
        if path is None:
            base_dir = Path(__file__).resolve().parents[1]  # .../src
            path = base_dir / "config" / "glossary.yaml"

        self.path = Path(path)
        self.replace_exact = {}
        self.replace_substring = {}

        self._load_glossary()

    def _load_glossary(self) -> None:
        """Carrega o glossário do YAML, se existir."""
        if not self.path.exists():
            logger.info(
                f"Glossário não encontrado em {self.path} – usando glossário vazio."
            )
            return

        try:
            try:
                import yaml  # type: ignore
            except ImportError:
                logger.warning(
                    "PyYAML não instalado – glossário será ignorado. "
                    "Instale com: pip install pyyaml"
                )
                return

            with self.path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if not isinstance(data, dict):
                logger.warning(
                    f"Glossário em {self.path} tem formato inválido (esperado dict)."
                )
                return

            self.replace_exact = data.get("replace_exact", {}) or {}
            self.replace_substring = data.get("replace_substring", {}) or {}

            logger.info(
                "Glossário carregado de "
                f"{self.path} "
                f"({len(self.replace_exact)} exatos, "
                f"{len(self.replace_substring)} substrings)."
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar glossário em {self.path}: {e}")
            # Mantém glossário vazio

    def apply(self, text: str) -> str:
        """
        Aplica as regras de glossário ao texto.

        Nunca levanta exceção: em erro, retorna o texto original.
        """
        if not text:
            return text

        try:
            result = text

            # 1) Substituições exatas por palavra inteira (case-sensitive)
            for src, dst in self.replace_exact.items():
                if not src:
                    continue
                pattern = r"\b" + re.escape(src) + r"\b"
                result = re.sub(pattern, dst, result)

            # 2) Substituições por substring simples (case-sensitive)
            for src, dst in self.replace_substring.items():
                if not src:
                    continue
                result = result.replace(src, dst)

            return result
        except Exception as e:
            logger.warning(f"Glossário: erro ao aplicar regras – {e}")
            return text


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
        if not api_key or not api_key.startswith("gsk_"):
            raise ValueError("API key inválida. Formato esperado: gsk_...")

        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

        logger.info(f"✓ GroqTranslator inicializado - modelo: {model}")

    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Traduz usando Groq API."""
        try:
            import requests

            # Mapear códigos para nomes completos
            lang_names = {
                "en": "English",
                "ko": "Korean",
                "pt": "Portuguese",
                "ja": "Japanese",
                "zh": "Chinese",
            }

            source_name = lang_names.get(source_lang, source_lang)
            target_name = lang_names.get(target_lang, target_lang)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Prompt especializado para diálogos de mangá/manhwa em PT-BR.
            system_prompt = (
                "You are a professional translator specialized in manga, manhwa, "
                "anime, webtoons and Japanese/Korean games. "
                f"Translate all input dialogue from {source_name} to natural, fluent "
                "Brazilian Portuguese. Keep the original meaning, tone and emotional "
                "nuance, and preserve character names and important terms "
                "(techniques, attacks, places, honorifics) when appropriate. "
                "Do NOT add explanations, notes, brackets or any extra text. "
                "Return ONLY the translated dialogue, without quotes."
            )

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                # Temperatura baixa para maior estabilidade na tradução
                "temperature": 0.1,
                "max_tokens": 500,
                "top_p": 1,
                "stream": False,
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                translated = data["choices"][0]["message"]["content"].strip()

                # Remover aspas extras se houver
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1]

                logger.debug(
                    f"Groq: '{text[:30]}...' → '{translated[:30]}...'"
                )
                return translated

            elif response.status_code == 429:
                logger.warning("Groq: Limite de taxa excedido")
                return None

            else:
                # Log detalhado do erro
                error_details = response.text if response.text else "Sem detalhes"
                logger.error(
                    f"Groq: HTTP {response.status_code} - {error_details}"
                )
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
            logger.error(
                "deep-translator não instalado. Execute: pip install deep-translator"
            )
            raise

    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Traduz usando Google Translate."""
        try:
            # deep-translator usa 'auto' para detecção automática
            source = source_lang if source_lang != "unknown" else "auto"
            translator = self.translator_class(
                source=source,
                target=target_lang,
            )
            translated = translator.translate(text)

            if translated and translated != text:
                logger.debug(
                    f"Google: '{text[:30]}...' → '{translated[:30]}...'"
                )
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
    - Modelo baixado: ollama pull qwen2.5:7b (ou outro)
    - Servidor rodando: ollama serve
    """

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
    ):
        """
        Inicializa tradutor Ollama.

        Args:
            model: Modelo a usar (llama3.1, qwen2.5:7b, etc)
            base_url: URL do servidor Ollama
        """
        self.model = model
        self.base_url = base_url

        # Testar conexão e verificar se o modelo existe via /api/tags
        try:
            import requests

            response = requests.get(f"{base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json() or {}

                # /api/tags geralmente retorna {"models": [{ "name": "...", ...}, ...]}
                raw_models = data.get("models", data)
                available_models = [
                    m.get("name") or m.get("model")
                    for m in raw_models
                    if isinstance(m, dict)
                ]

                if available_models and self.model not in available_models:
                    logger.warning(
                        f"Ollama: modelo '{self.model}' não encontrado em {base_url}. "
                        f"Execute 'ollama pull {self.model}' para baixá-lo."
                    )

                logger.info(
                    f"✓ OllamaTranslator inicializado - modelo: {model} "
                    f"(servidor em {base_url})"
                )
            else:
                logger.warning(
                    f"Ollama: servidor não responde em {base_url} "
                    f"(status {response.status_code})"
                )
        except Exception as e:
            logger.warning(f"Ollama: não conectado a {base_url} - {e}")

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[str]:
        """Traduz usando Ollama local."""
        try:
            import requests

            # Mapear códigos de idioma para nomes mais legíveis (apenas para o prompt)
            lang_names = {
                "en": "English",
                "ko": "Korean",
                "pt": "Portuguese",
                "ja": "Japanese",
                "zh": "Chinese",
            }
            target_name = lang_names.get(target_lang, target_lang)

            # Prompt especializado para diálogos de mangá/manhwa em PT-BR.
            prompt = (
                "You are a professional translator specialized in manga, manhwa, "
                "anime and games. Translate the following dialogue to natural, "
                "fluent Brazilian Portuguese. Keep the original meaning, tone and "
                "emotional nuance, and preserve character names and important terms "
                "(techniques, attacks, places, honorifics) when appropriate. "
                "Do NOT add explanations, notes, brackets or any extra text. "
                "Return only the translated dialogue.\n\n"
                f"{text}"
            )

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    # Temperatura baixa para maior consistência
                    "temperature": 0.1,
                    "num_predict": 500,
                },
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                translated = (data.get("response") or "").strip()
                if translated:
                    logger.debug(
                        f"Ollama: '{text[:30]}...' → '{translated[:30]}...'"
                    )
                    return translated
                return None

            # HTTP diferente de 200: logar detalhes se existirem
            error_details = response.text if response.text else "Sem detalhes"
            logger.error(
                f"Ollama: HTTP {response.status_code} - {error_details}"
            )
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
            "hello": "olá",
            "world": "mundo",
            "thank you": "obrigado",
            "thanks": "obrigado",
            "yes": "sim",
            "no": "não",
            "please": "por favor",
            "sorry": "desculpe",
            "good": "bom",
            "bad": "ruim",
            "morning": "manhã",
            "night": "noite",
            "day": "dia",
            "time": "tempo",
            "today": "hoje",
            "tomorrow": "amanhã",
            "yesterday": "ontem",
        }

        logger.info("✓ OfflineTranslator inicializado (dicionário básico)")

    def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
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
    1. Groq (se configurado)  — otimizado para mangá/manhwa PT-BR
    2. Google Translate
    3. Ollama (se habilitado) — também otimizado para diálogos de mangá/manhwa PT-BR
    4. Offline (fallback final)

    Após a tradução, aplica um glossário de termos específicos (se configurado).
    """

    def __init__(
        self,
        groq_key: Optional[str] = None,
        google_enabled: bool = True,
        ollama_enabled: bool = False,
        groq_model: str = "llama-3.3-70b-versatile",
        ollama_model: str = "llama3.1",
        ollama_url: str = "http://localhost:11434",
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
                self.translators.append(("groq", translator))
            except Exception as e:
                logger.warning(f"Groq não inicializado: {e}")

        # 2. Google Translate (sempre habilitado se disponível)
        if google_enabled:
            try:
                translator = GoogleTranslator()
                self.translators.append(("google", translator))
            except Exception as e:
                logger.warning(f"Google não inicializado: {e}")

        # 3. Ollama (se habilitado explicitamente)
        if ollama_enabled:
            try:
                translator = OllamaTranslator(ollama_model, ollama_url)
                self.translators.append(("ollama", translator))
            except Exception as e:
                logger.warning(f"Ollama não inicializado: {e}")

        # 4. Fallback offline (sempre presente)
        self.translators.append(("offline", OfflineTranslator()))

        # Pós-processador de glossário (aplicado a qualquer provedor)
        self.glossary = GlossaryPostProcessor()

        # Log dos tradutores ativos
        logger.info(
            f"TranslationService: {len(self.translators)} tradutor(es) ativo(s)"
        )
        for name, _ in self.translators:
            logger.info(f" → {name}")

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "pt",
    ) -> TranslationResult:
        """
        Traduz texto com fallback automático.

        Tenta cada tradutor em ordem até obter sucesso.
        Aplica o glossário ao texto traduzido antes de devolver.
        Preenche métricas de tempo de processamento (processing_time).
        """
        start_time = time.perf_counter()

        if not text or len(text.strip()) == 0:
            elapsed = time.perf_counter() - start_time
            return TranslationResult(
                original_text=text,
                translated_text="",
                source_language=source_lang,
                target_language=target_lang,
                provider=TranslationProvider.OFFLINE,
                confidence=0.0,
                processing_time=elapsed,
                from_cache=False,
            )

        # Tentar cada tradutor
        for provider_name, translator in self.translators:
            try:
                translated = translator.translate(
                    text, source_lang, target_lang
                )

                if translated:
                    # Aplicar glossário antes de validar e retornar
                    translated = self.glossary.apply(translated)

                if (
                    translated
                    and translated != text
                    and len(translated.strip()) > 0
                ):
                    elapsed = time.perf_counter() - start_time
                    return TranslationResult(
                        original_text=text,
                        translated_text=translated,
                        source_language=source_lang,
                        target_language=target_lang,
                        provider=TranslationProvider(provider_name),
                        confidence=1.0
                        if provider_name != "offline"
                        else 0.5,
                        processing_time=elapsed,
                        from_cache=False,  # cache real é gerenciado no ProcessingPipeline
                    )

            except Exception as e:
                logger.warning(
                    f"Falha no tradutor '{provider_name}': {e}"
                )
                continue

        # Se todos falharam, retornar original
        elapsed = time.perf_counter() - start_time
        logger.error(f"Nenhum tradutor conseguiu traduzir: '{text}'")
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language=source_lang,
            target_language=target_lang,
            provider=TranslationProvider.OFFLINE,
            confidence=0.0,
            processing_time=elapsed,
            from_cache=False,
        )

    def get_active_providers(self) -> list:
        """Retorna lista de provedores ativos."""
        return [name for name, _ in self.translators]

    def test_all_providers(self) -> dict:
        """
        Testa todos os provedores com uma frase simples.

        Nota: também aplica o glossário para refletir o comportamento real.
        """
        test_text = "Hello world"
        results = {}

        for provider_name, translator in self.translators:
            try:
                translated = translator.translate(
                    test_text, "en", "pt"
                )
                if translated:
                    translated = self.glossary.apply(translated)

                results[provider_name] = {
                    "status": "ok" if translated else "failed",
                    "translation": translated,
                }
            except Exception as e:
                results[provider_name] = {
                    "status": "error",
                    "error": str(e),
                }

        return results
