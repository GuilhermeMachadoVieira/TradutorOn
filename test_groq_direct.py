"""Teste direto da API Groq com modelos atualizados."""

import os
import requests
from dotenv import load_dotenv

load_dotenv('config/.env')
api_key = os.getenv('GROQ_API_KEY')

print(f"🔑 API Key: {api_key[:15]}..." if api_key else "❌ Chave não encontrada")
print(f"📏 Comprimento: {len(api_key)}" if api_key else "")

if not api_key:
    print("\n❌ Configure GROQ_API_KEY no arquivo config/.env")
    exit(1)

# Modelos atuais da Groq (dezembro 2025)
models = [
    "llama-3.3-70b-versatile",      # Mais novo, melhor qualidade
    "llama-3.1-8b-instant",         # Rápido
    "mixtral-8x7b-32768",           # Alternativa
]

print(f"\n🧪 Testando {len(models)} modelos Groq...\n")

for model in models:
    print(f"📝 Modelo: {model}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Translate to Portuguese: Hello, how are you?"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 100
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data['choices'][0]['message']['content'].strip()
            print(f"   ✅ SUCESSO: {result}")
        else:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Erro desconhecido')
            print(f"   ❌ HTTP {response.status_code}: {error_msg[:80]}")
            
    except Exception as e:
        print(f"   ❌ Exceção: {str(e)[:80]}")
    
    print()

print("="*60)
print("💡 Use o primeiro modelo que funcionou em default_config.yaml")
print("="*60)
