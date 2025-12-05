"""Script para testar individualmente cada tradutor."""

from src.config.logger import LoggerSetup
from src.config.settings import SettingsManager
from src.translation.translator import (
    GroqTranslator,
    GoogleTranslator,
    OllamaTranslator,
    TranslationService
)

LoggerSetup.initialize(level="INFO")
settings = SettingsManager()

print("\n" + "="*60)
print("🧪 TESTE DE TRADUTORES")
print("="*60)

test_text = "Hello, how are you?"
source = "en"
target = "pt"

# Teste 1: Groq
print("\n1️⃣ TESTANDO GROQ:")
groq_key = settings.get_api_key('groq')
if groq_key:
    try:
        groq = GroqTranslator(groq_key)
        result = groq.translate(test_text, source, target)
        print(f"✅ Resultado: {result}")
    except Exception as e:
        print(f"❌ Erro: {e}")
else:
    print("⚠️ GROQ_API_KEY não configurada")

# Teste 2: Google
print("\n2️⃣ TESTANDO GOOGLE:")
try:
    google = GoogleTranslator()
    result = google.translate(test_text, source, target)
    print(f"✅ Resultado: {result}")
except Exception as e:
    print(f"❌ Erro: {e}")

# Teste 3: Ollama (se habilitado)
print("\n3️⃣ TESTANDO OLLAMA:")
if settings.get('translation.ollama.enabled'):
    try:
        ollama = OllamaTranslator()
        result = ollama.translate(test_text, source, target)
        print(f"✅ Resultado: {result}")
    except Exception as e:
        print(f"❌ Erro: {e}")
else:
    print("⚠️ Ollama desabilitado em config.yaml")

# Teste 4: Serviço completo com fallback
print("\n4️⃣ TESTANDO SERVIÇO COMPLETO:")
service = TranslationService(
    groq_key=groq_key,
    google_enabled=True,
    ollama_enabled=False
)
result = service.translate(test_text, source, target)
print(f"✅ Provider usado: {result.provider.value}")
print(f"✅ Resultado: {result.translated_text}")

print("\n" + "="*60)
