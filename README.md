# 🌐 Manga Translator Pro

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green.svg)](https://pypi.org/project/PyQt6/)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.8%2B-orange.svg)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Tradutor de Tela em Tempo Real com OCR e IA**  
> Traduza mangás, manhwas, jogos e qualquer conteúdo visual automaticamente enquanto você lê/joga [web:68][web:70][web:72].

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Instalação](#-instalação)
- [Uso Rápido](#-uso-rápido)
- [Configuração Avançada](#-configuração-avançada)
- [Tecnologias](#-tecnologias)
- [Roadmap](#-roadmap)
- [Troubleshooting](#-troubleshooting)
- [Contribuindo](#-contribuindo)

---

## 🎯 Visão Geral

**Manga Translator Pro** é um sistema de tradução em tempo real que captura automaticamente texto de qualquer região da tela, reconhece caracteres usando OCR de alta precisão (PaddleOCR) e traduz instantaneamente para o seu idioma preferido usando múltiplos provedores de IA [web:70][web:74].

### O Que Este Projeto É

Um **tradutor universal de tela** que permite:
- 📖 Ler mangás/manhwas não traduzidos em tempo real
- 🎮 Jogar visual novels e jogos japoneses/coreanos sem barreiras linguísticas
- 📺 Assistir streams/vídeos estrangeiros com legendas instantâneas
- 🌐 Traduzir qualquer conteúdo visual sem precisar de capturas manuais

### O Que Este Projeto NÃO É

- ❌ Não é um tradutor de arquivos PDF/EPUB (use ferramentas específicas para isso)
- ❌ Não substitui a leitura do original (pode haver imprecisões de tradução)
- ❌ Não é um editor de imagens (não modifica o conteúdo original)

---

## ✨ Funcionalidades

### 🎯 Captura Inteligente
- **Seleção Visual de Área**: Arraste e solte para definir exatamente onde traduzir
- **Detecção Automática de Mudanças**: Captura apenas quando o conteúdo muda (economia de recursos)
- **Multi-Monitor**: Suporte completo para configurações de múltiplos monitores
- **Cache Persistente**: Traduções armazenadas localmente para acesso instantâneo [web:70]

### 🤖 OCR de Alta Precisão
- **PaddleOCR v3.0**: Engine de OCR state-of-the-art com 91%+ de precisão [web:71][web:74]
- **Multi-Idioma**: Suporte para Inglês, Coreano, Japonês, Chinês e mais
- **Reconhecimento Robusto**: Funciona com fontes estilizadas, textos curvos e baixa resolução
- **Processamento Paralelo**: Workers dedicados para OCR não bloquear a captura

### 🌍 Tradução Multi-Provedor
- **Groq API** (Prioritário): LLM gratuito (Llama 3.3 70B) com 6.000 req/min [web:68]
- **Google Translate** (Fallback): 100+ idiomas suportados via deep-translator
- **Offline Fallback**: Dicionário básico quando sem internet
- **Cache SQLite**: Tradução instantânea para textos já vistos (< 10ms)

### 🖥️ Interface Moderna
- **GUI PyQt6**: Interface dark theme (Catppuccin) responsiva e intuitiva
- **Estatísticas em Tempo Real**: Contador de traduções, caracteres processados, tempo decorrido
- **Log Integrado**: Acompanhe o que está sendo traduzido em tempo real
- **Minimização Automática**: GUI se esconde durante tradução para não ser capturada

### 🔧 Configuração Flexível
- **YAML Config**: Personalize frame rate, idiomas, thresholds de confiança OCR
- **Variáveis de Ambiente**: Gerencie API keys com segurança via `.env`
- **Persistência de Área**: Última área selecionada é restaurada automaticamente

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      MANGA TRANSLATOR PRO                    │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼─────┐       ┌──────▼──────┐     ┌──────▼──────┐
    │ GUI      │       │ Pipeline    │     │ Config      │
    │ (PyQt6)  │       │ Processor   │     │ Manager     │
    └────┬─────┘       └──────┬──────┘     └──────┬──────┘
         │                    │                    │
         │          ┌─────────┼─────────┐          │
         │          │         │         │          │
    ┌────▼─────┐  ┌─▼─────┐ ┌▼──────┐ ┌▼─────┐   │
    │ Area     │  │Screen │ │ OCR   │ │Trans │   │
    │ Selector │  │Capture│ │Engine │ │lator │   │
    └──────────┘  └───┬───┘ └───┬───┘ └───┬──┘   │
                      │         │         │       │
                      │    ┌────▼─────────▼───┐   │
                      │    │   Cache Manager  │   │
                      │    │   (SQLite)       │   │
                      │    └──────────────────┘   │
                      │                           │
                 ┌────▼───────────────────────────▼───┐
                 │     Settings (YAML + .env)         │
                 └────────────────────────────────────┘
```

### Componentes Principais

| Componente | Responsabilidade | Tecnologia |
|------------|------------------|------------|
| **GUI** | Interface gráfica, controle de pipeline | PyQt6 |
| **AreaSelector** | Overlay transparente para seleção visual | PyQt6 Widgets |
| **ScreenCapturer** | Captura de screenshots com detecção de mudanças | MSS, PIL |
| **OCREngine** | Reconhecimento de texto em imagens | PaddleOCR |
| **TranslationService** | Orquestração de múltiplos tradutores | Groq API, deep-translator |
| **CacheManager** | Persistência de traduções e OCR | SQLite3 |
| **ProcessingPipeline** | Coordenação de captura → OCR → tradução | Threading, Queue |

---

## 📦 Instalação

### Pré-requisitos

- **Python 3.10+** (recomendado 3.11)
- **Windows 10/11** (Linux/Mac em desenvolvimento)
- **8GB RAM** (mínimo) / 16GB RAM (recomendado para GPU)
- **GPU NVIDIA** (opcional, para OCR acelerado)

### Passo a Passo

1. **Clone o repositório:**
```
git clone https://github.com/GuilhermeMachadoVieira/TradutorOn.git
cd TradutorOn
```

2. **Crie ambiente virtual:**
```
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Instale dependências:**
```
pip install -r requirements.txt
```

4. **Configure API keys:**
```
# Crie config/.env
echo GROQ_API_KEY=gsk_seu_token_aqui > config\.env
```

5. **Execute:**
```
python main.py
```

### Obter API Keys Gratuitas

#### Groq API (Recomendado)
1. Acesse [console.groq.com](https://console.groq.com)
2. Crie uma conta gratuita
3. Vá em "API Keys" → "Create API Key"
4. Copie a chave e cole em `config/.env`

**Limites gratuitos:**
- 6.000 requisições/minuto
- 30.000 requisições/dia
- Modelo: Llama 3.3 70B Versatile

---

## 🚀 Uso Rápido

### 1. Selecionar Área de Captura

**Opção A: Seleção Visual (Recomendado)**
1. Clique em **"📍 Selecionar Área (Drag-Drop)"**
2. A GUI será minimizada
3. Arraste um retângulo sobre a região do mangá/jogo
4. Solte para confirmar
5. GUI reaparece com coordenadas salvas

**Opção B: Área Manual**
1. Edite `config/default_config.yaml`:
```
capture:
  area:
    x1: 100
    y1: 100
    x2: 1820
    y2: 980
```

### 2. Iniciar Tradução

1. Clique **"🚀 Iniciar Tradução"**
2. GUI será minimizada automaticamente
3. Abra o mangá/jogo na área selecionada
4. Veja traduções aparecerem no log (ao restaurar GUI)

### 3. Parar Tradução

1. Restaure a GUI da barra de tarefas
2. Clique **"⏹ Parar"**
3. Veja estatísticas finais

### Atalhos de Teclado (Futuros)

| Atalho | Ação |
|--------|------|
| `F9` | Capturar e traduzir agora |
| `F10` | Toggle monitoramento automático |
| `ESC` | Cancelar seleção de área |

---

## ⚙️ Configuração Avançada

### config/default_config.yaml

```
# Configuração de Captura
capture:
  frame_rate: 2  # FPS de captura (1-5 recomendado)
  change_threshold: 0.05  # Sensibilidade de mudança (0.01-0.1)
  min_change_area: 0.01  # Área mínima de mudança (%)

# Configuração de OCR
ocr:
  languages: ['en', 'ko', 'ja']  # Idiomas suportados
  use_gpu: false  # true para GPU NVIDIA (requer CUDA)
  confidence_threshold: 0.5  # Confiança mínima (0.0-1.0)
  use_angle_cls: true  # Detectar texto rotacionado

# Configuração de Tradução
translation:
  source_lang: 'en'  # Idioma de origem (auto, en, ko, ja, zh)
  target_lang: 'pt'  # Idioma de destino
  batch_size: 10  # Agrupar N textos por tradução
  timeout: 10  # Timeout por requisição (segundos)

# Cache
cache:
  enabled: true
  max_size_mb: 500  # Tamanho máximo do DB SQLite
  auto_cleanup: true  # Limpar automaticamente entradas antigas
```

### config/.env

```
# Groq API (Prioritário)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx

# Ollama (Opcional - Local)
OLLAMA_ENABLED=false
OLLAMA_MODEL=llama3.1
OLLAMA_URL=http://localhost:11434

# Google Translate (Fallback - Sempre Habilitado)
GOOGLE_TRANSLATE_ENABLED=true
```

---

## 🛠️ Tecnologias

### Core Stack
- **[Python 3.11](https://www.python.org/)**: Linguagem principal
- **[PyQt6](https://pypi.org/project/PyQt6/)**: Framework GUI moderno [web:76]
- **[PaddleOCR 3.0](https://github.com/PaddlePaddle/PaddleOCR)**: Engine OCR state-of-the-art [web:74][web:77]
- **[MSS](https://python-mss.readthedocs.io/)**: Screenshot multiplataforma ultra-rápido

### Tradução
- **[Groq API](https://console.groq.com/)**: LLM gratuito (Llama 3.3 70B)
- **[deep-translator](https://github.com/nidhaloff/deep-translator)**: Google Translate wrapper
- **SQLite3**: Cache persistente de traduções

### Utilities
- **[Loguru](https://github.com/Delgan/loguru)**: Logging estruturado
- **[Pillow (PIL)](https://pillow.readthedocs.io/)**: Manipulação de imagens
- **[PyYAML](https://pyyaml.org/)**: Parsing de configuração
- **[python-dotenv](https://github.com/theskumar/python-dotenv)**: Gerenciamento de .env

---

## 🗺️ Roadmap

### ✅ Fase 1: Core (Concluída)
- [x] GUI PyQt6 com AreaSelector visual
- [x] ProcessingPipeline integrado (Captura → OCR → Tradução)
- [x] Multi-provedor de tradução (Groq + Google + Offline)
- [x] Cache SQLite persistente
- [x] Estatísticas em tempo real
- [x] Persistência de área selecionada

### 🚧 Fase 2: Overlay (Em Desenvolvimento)
- [ ] TranslationOverlay: Janelas flutuantes com tradução na tela
- [ ] Auto-hide após N segundos
- [ ] Posicionamento correto sobre texto original
- [ ] Fonte customizável e background transparente

### 📅 Fase 3: Inteligência (Planejado)
- [ ] Agrupamento inteligente de linhas OCR (balões de mangá)
- [ ] Detecção automática de idioma (skip português)
- [ ] Filtro de confiança OCR (ignorar ruído)
- [ ] Histórico de traduções (navegável)

### 🎯 Fase 4: UX/Distribuição (Planejado)
- [ ] Painel de configuração na GUI (dropdowns, sliders)
- [ ] Atalhos de teclado globais (F9, F10)
- [ ] Modo de baixo consumo (CPU/RAM otimizado)
- [ ] Build standalone (.exe com PyInstaller)
- [ ] Suporte Linux/Mac

### 🌟 Fase 5: Recursos Avançados (Futuro)
- [ ] Suporte a vídeo/stream (tradução de legendas ao vivo)
- [ ] Plugin de browser (traduzir páginas web)
- [ ] API REST (usar como serviço)
- [ ] Modo colaborativo (compartilhar traduções)

---

## ❓ Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'area_selector'"
**Causa:** `area_selector.py` não está na raiz do projeto.  
**Solução:** Certifique-se que `area_selector.py` está ao lado de `main.py`.

### ❌ "Erro no OCR: could not execute a primitive"
**Causa:** PaddleOCR tentando processar frames muito rápido ou imagens com problemas.  
**Solução:**
1. Reduza `capture.frame_rate` em `config/default_config.yaml` (tente 1 fps)
2. Aumente `capture.change_threshold` (tente 0.1)
3. Certifique-se que a área selecionada contém texto legível

### ⚠️ "Nenhum tradutor conseguiu traduzir"
**Causa:** Todos os provedores falharam (sem internet, API key inválida, texto sem tradução).  
**Solução:**
1. Verifique internet: `ping 8.8.8.8`
2. Valide API key: `echo %GROQ_API_KEY%`
3. Teste Google Translate: `pip install --upgrade deep-translator`

### 🐌 "Tradução muito lenta"
**Causa:** OCR rodando em CPU sem aceleração.  
**Solução:**
1. **Com GPU NVIDIA:**
   ```
   pip install paddlepaddle-gpu
   ```
   Edite `config/default_config.yaml`:
   ```
   ocr:
     use_gpu: true
   ```
2. **Sem GPU:**
   - Reduza `capture.frame_rate` para 1 fps
   - Aumente `translation.batch_size` para 20

### 🪟 "GUI ainda está sendo capturada"
**Causa:** Área selecionada inclui a janela da GUI.  
**Solução:**
1. Clique **"🗑️ Limpar Área Salva"**
2. Selecione novamente **APENAS** a região do mangá/jogo
3. Certifique-se que a GUI está FORA da área selecionada

### 📁 "Banco de dados corrompido"
**Causa:** Encerramento forçado do programa durante escrita no cache.  
**Solução:**
```
del cache\translations.db
python main.py  # Cache será recriado
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Siga o fluxo:

1. **Fork o projeto**
2. **Crie uma branch:** `git checkout -b feature/minha-feature`
3. **Commit suas mudanças:** `git commit -m 'feat: adiciona overlay de tradução'`
4. **Push para a branch:** `git push origin feature/minha-feature`
5. **Abra um Pull Request**

### Diretrizes

- Use [Conventional Commits](https://www.conventionalcommits.org/)
- Adicione testes para novos recursos
- Atualize a documentação conforme necessário
- Siga PEP 8 (use `black` para formatação)

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🙏 Agradecimentos

- **[PaddleOCR Team](https://github.com/PaddlePaddle/PaddleOCR)** - Engine OCR excepcional [web:74]
- **[Groq](https://groq.com/)** - API LLM gratuita e ultra-rápida
- **[PyQt6](https://riverbankcomputing.com/software/pyqt/)** - Framework GUI poderoso
- **Comunidade de Manga Translation** - Inspiração e feedback [web:68][web:72]

---

## 📧 Contato

- **GitHub:** [@GuilhermeMachadoVieira](https://github.com/GuilhermeMachadoVieira)
- **Issues:** [github.com/GuilhermeMachadoVieira/TradutorOn/issues](https://github.com/GuilhermeMachadoVieira/TradutorOn/issues)

---

<div align="center">

**Feito com ❤️ por desenvolvedores que amam mangás**

[⬆ Voltar ao topo](#-manga-translator-pro)

</div>
```

***
