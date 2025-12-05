"""
Exemplo de uso do Manga Translator Pro - Fase 1.

Este script demonstra como usar a pipeline completa.
"""

import time
from src.config.logger import LoggerSetup
from src.config.settings import SettingsManager
from src.capture.monitor_detector import MonitorDetector
from src.pipeline.processor import ProcessingPipeline
from src.utils.types import ScreenArea


def on_translation_result(results):
    """
    Callback chamado quando há novos resultados de tradução.
    
    Args:
        results: Lista de dicionários com traduções
    """
    if not results:
        return
    
    print("\n" + "="*60)
    print("📝 TRADUÇÃO RECEBIDA:")
    print("="*60)
    
    for idx, result in enumerate(results, 1):
        print(f"\n{idx}. Original ({result['language']}): {result['original']}")
        print(f"   Traduzido: {result['translated']}")
        print(f"   Confiança OCR: {result['confidence']*100:.2f}%")
        print(f"   Posição: {result['bbox']}")


def main():
    """Função principal de demonstração."""
    
    print("\n" + "="*60)
    print("🌐 MANGA TRANSLATOR PRO - FASE 1")
    print("="*60)
    
    # 1. Inicializar logger
    LoggerSetup.initialize(level="INFO")
    
    # 2. Carregar configurações
    print("\n⚙️ Carregando configurações...")
    settings = SettingsManager()
    
    # 3. Detectar monitores
    print("\n📺 Detectando monitores...")
    detector = MonitorDetector()
    
    for monitor in detector.monitors:
        print(f"\n  📍 Monitor {monitor.index}: {monitor.name}")
        print(f"     Resolução: {monitor.width}x{monitor.height}")
        print(f"     Posição global: ({monitor.x}, {monitor.y})")
        print(f"     DPI: {monitor.dpi}")
    
    # 4. Definir área de captura
    print("\n🎯 Configurando área de captura...")
    primary = detector.get_primary()
    
    # Área grande (quase tela toda, exceto bordas)
    area = ScreenArea(
        x1=primary.x + 100,
        y1=primary.y + 100,
        x2=primary.x + primary.width - 100,
        y2=primary.y + primary.height - 100,
        monitor_index=0
    )
    
    print(f"  Área selecionada:")
    print(f"    X: {area.x1} → {area.x2} (largura: {area.width}px)")
    print(f"    Y: {area.y1} → {area.y2} (altura: {area.height}px)")
    print(f"    Tamanho: {area.area/1_000_000:.2f} milhões de pixels")
    
    # 5. Criar e iniciar pipeline
    print("\n🚀 Iniciando pipeline de processamento...")
    pipeline = ProcessingPipeline(
        settings_manager=settings,
        on_result_callback=on_translation_result,
        num_ocr_workers=2
    )
    
    pipeline.start(area)
    
    # 6. Monitorar por 30 segundos
    duration = 30
    print(f"\n✅ Pipeline iniciada! Monitorando por {duration} segundos...")
    print("   (Abra um mangá/livro em inglês ou coreano na tela)")
    
    try:
        for i in range(duration):
            time.sleep(1)
            
            # Mostrar estatísticas a cada 5 segundos
            if (i + 1) % 5 == 0:
                stats = pipeline.get_stats()
                cache_stats = stats.get('cache', {})
                print(f"\n  ⏱️ {i+1}s - Cache: {cache_stats.get('total_translations', 0)} traduções, "
                      f"DB: {cache_stats.get('db_size_mb', 0):.2f}MB")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário")
    
    finally:
        # 7. Parar pipeline
        print("\n🛑 Parando pipeline...")
        pipeline.stop()
        
        # 8. Mostrar estatísticas finais
        print("\n" + "="*60)
        print("📊 ESTATÍSTICAS")
        print("="*60)
        
        stats = pipeline.get_stats()
        cache_stats = stats.get('cache', {})
        
        print(f"\n📦 Cache:")
        print(f"   Traduções armazenadas: {cache_stats.get('total_translations', 0)}")
        print(f"   Resultados OCR: {cache_stats.get('total_ocr', 0)}")
        print(f"   Tamanho DB: {cache_stats.get('db_size_mb', 0):.2f} MB")
        print(f"   Uso do cache: {cache_stats.get('cache_full_percent', 0):.3f}%")
        
        print(f"\n🔤 OCR Engine:")
        print(f"   Modelo: PaddleOCR")
        print(f"   Idiomas: {settings.get('ocr.languages')}")
        print(f"   Cache entradas: {len(pipeline.ocr_engine.cache)}/100")
        
        print("\n" + "="*60)
        print("✨ Exemplo concluído com sucesso!")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
