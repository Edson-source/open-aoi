"""
Advanced Examples: Extending Plate Alignment Inspection Handler

Este arquivo mostra exemplos avançados de como estender ou customizar 
a inspeção de alinhamento de placas para casos mais específicos.
"""

import numpy as np
import cv2 as cv
from typing import List, Tuple, Dict
from pathlib import Path

# ============================================================================
# EXEMPLO 1: Usar o handler diretamente sem o portal
# ============================================================================

def example_1_direct_usage():
    """
    Exemplo de como usar o handler diretamente em código Python,
    sem passar pelo portal.
    """
    import sys
    sys.path.insert(0, './modules_production')
    
    import plate_alignment_inspection
    
    # Carrega imagens
    golden_img = cv.imread('golden_image.jpg')  # BGR
    test_img = cv.imread('test_image.jpg')      # BGR
    
    # Converte test para RGB (como vem da câmera)
    test_img_rgb = cv.cvtColor(test_img, cv.COLOR_BGR2RGB)
    
    # Define zonas de inspeção
    zones = [
        type('Zone', (), {
            'id': i,
            'rotation': 0,
            'cc': type('CC', (), {
                'stat_left': 100 + i*150,
                'stat_top': 100,
                'stat_width': 100,
                'stat_height': 100
            })
        })
        for i in range(4)
    ]
    
    # Configura ambiente
    environment = {
        'SIMILARITY_THRESHOLD': '0.85',
        'MAX_FEATURES': '5000',
        'KEEP_PERCENT': '0.2',
        'ALIGNMENT_METHOD': 'ORB'
    }
    
    # Executa inspeção
    inspector = plate_alignment_inspection.module
    logs = inspector.process(environment, test_img_rgb, golden_img, zones)
    
    # Processa resultados
    for log in logs:
        print(f"{'✓' if log.decision else '✗'} {log.description}")
    
    return logs


# ============================================================================
# EXEMPLO 2: Handler Customizado com Histórico
# ============================================================================

class PlateAlignmentWithHistory:
    """
    Extensão do handler que mantém histórico de inspeções
    e detecta degradação ao longo do tempo.
    """
    
    def __init__(self, max_history: int = 100):
        self.history = []
        self.max_history = max_history
        self.zone_trend = {}
    
    def record_inspection(self, zone_id: int, similarity: float, timestamp: str):
        """Registra resultado de inspeção"""
        record = {
            'zone_id': zone_id,
            'similarity': similarity,
            'timestamp': timestamp
        }
        self.history.append(record)
        
        # Mantém apenas o histórico recente
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Atualiza tendência
        if zone_id not in self.zone_trend:
            self.zone_trend[zone_id] = []
        self.zone_trend[zone_id].append(similarity)
    
    def detect_degradation(self, zone_id: int, window: int = 10) -> bool:
        """
        Detecta se uma zona está se degradando gradualmente.
        Retorna True se há tendência de piora.
        """
        if zone_id not in self.zone_trend:
            return False
        
        trend = self.zone_trend[zone_id][-window:]
        if len(trend) < window:
            return False
        
        # Calcula regressão linear simples
        x = np.arange(len(trend))
        z = np.polyfit(x, trend, 1)
        slope = z[0]
        
        # Se slope negativo e significativo, há degradação
        return slope < -0.01
    
    def get_zone_stats(self, zone_id: int) -> Dict:
        """Retorna estatísticas de uma zona"""
        if zone_id not in self.zone_trend:
            return {}
        
        values = np.array(self.zone_trend[zone_id])
        return {
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'latest': float(values[-1]),
            'degrading': self.detect_degradation(zone_id)
        }


# ============================================================================
# EXEMPLO 3: Handler com Masking para Áreas Específicas
# ============================================================================

class PlateAlignmentWithMasking:
    """
    Variação que permite excluir certas áreas da comparação
    (útil para logos, textos que mudam, etc).
    """
    
    def create_mask(self, image_shape: Tuple[int, int], 
                   exclude_zones: List[Dict]) -> np.ndarray:
        """
        Cria máscara para ignorar certas áreas.
        
        Args:
            image_shape: (height, width) da imagem
            exclude_zones: Lista de dicts com {x, y, width, height}
        
        Returns:
            Máscara booleana
        """
        mask = np.ones(image_shape[:2], dtype=bool)
        
        for zone in exclude_zones:
            x, y = zone['x'], zone['y']
            w, h = zone['width'], zone['height']
            mask[y:y+h, x:x+w] = False
        
        return mask
    
    def compute_masked_similarity(self, test_chunk: np.ndarray,
                                  template_chunk: np.ndarray,
                                  mask: np.ndarray) -> float:
        """Computa similaridade apenas na área da máscara"""
        # Aplica máscara
        test_masked = test_chunk.copy()
        template_masked = template_chunk.copy()
        
        test_masked[~mask] = 0
        template_masked[~mask] = 0
        
        # Calcula histograma apenas na área masked
        if len(test_masked.shape) == 3:
            test_gray = cv.cvtColor(test_masked, cv.COLOR_RGB2GRAY)
            template_gray = cv.cvtColor(template_masked, cv.COLOR_BGR2GRAY)
        else:
            test_gray = test_masked
            template_gray = template_masked
        
        hist_test = cv.calcHist([test_gray], [0], mask.astype(np.uint8), [256], [0, 256])
        hist_template = cv.calcHist([template_gray], [0], mask.astype(np.uint8), [256], [0, 256])
        
        hist_test = cv.normalize(hist_test, hist_test).flatten()
        hist_template = cv.normalize(hist_template, hist_template).flatten()
        
        return cv.compareHist(hist_test, hist_template, cv.HISTCMP_CORR)


# ============================================================================
# EXEMPLO 4: Handler Multi-Template (várias golden images)
# ============================================================================

class PlateAlignmentMultiTemplate:
    """
    Para placas com várias versões/modelos, permite escolher
    a golden image mais similar para comparação.
    """
    
    def __init__(self, golden_images_dir: str):
        self.golden_images = {}
        self.load_golden_images(golden_images_dir)
    
    def load_golden_images(self, directory: str):
        """Carrega todas as golden images de um diretório"""
        for img_path in Path(directory).glob('*.jpg'):
            name = img_path.stem
            img = cv.imread(str(img_path))
            self.golden_images[name] = img
    
    def find_best_template(self, test_image: np.ndarray) -> Tuple[str, np.ndarray, float]:
        """
        Encontra a golden image mais similar à imagem de teste.
        
        Returns:
            (template_name, template_image, similarity_score)
        """
        best_match = None
        best_score = -1
        best_image = None
        
        for name, golden in self.golden_images.items():
            # Resize para mesmo tamanho
            h, w = golden.shape[:2]
            test_resized = cv.resize(test_image, (w, h))
            
            # Computa similaridade global
            if len(test_resized.shape) == 3:
                test_gray = cv.cvtColor(test_resized, cv.COLOR_RGB2GRAY)
                golden_gray = cv.cvtColor(golden, cv.COLOR_BGR2GRAY)
            else:
                test_gray = test_resized
                golden_gray = golden
            
            hist_test = cv.calcHist([test_gray], [0], None, [256], [0, 256])
            hist_golden = cv.calcHist([golden_gray], [0], None, [256], [0, 256])
            
            hist_test = cv.normalize(hist_test, hist_test).flatten()
            hist_golden = cv.normalize(hist_golden, hist_golden).flatten()
            
            score = cv.compareHist(hist_test, hist_golden, cv.HISTCMP_CORR)
            
            if score > best_score:
                best_score = score
                best_match = name
                best_image = golden
        
        return best_match, best_image, best_score


# ============================================================================
# EXEMPLO 5: Alertas e Escalation
# ============================================================================

class InspectionAlertSystem:
    """
    Sistema de alertas para escalar problemas detectados.
    """
    
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback or self.default_alert
        self.failure_counts = {}  # Contador de falhas consecutivas por zona
    
    def process_logs(self, logs: List, threshold_consecutive: int = 3):
        """
        Processa logs e gera alertas se necessário.
        
        Args:
            logs: Lista de InspectionLog retornados
            threshold_consecutive: Quantas falhas seguidas para gerar alerta
        """
        for log in logs:
            if not log.decision:  # Falha
                # Extrai zone ID do log
                zone_id = self.extract_zone_id(log.description)
                
                if zone_id not in self.failure_counts:
                    self.failure_counts[zone_id] = 0
                
                self.failure_counts[zone_id] += 1
                
                # Se atingiu threshold, gera alerta
                if self.failure_counts[zone_id] >= threshold_consecutive:
                    self.alert_callback(
                        zone_id=zone_id,
                        failure_count=self.failure_counts[zone_id],
                        message=log.description
                    )
            else:  # Passou
                zone_id = self.extract_zone_id(log.description)
                if zone_id in self.failure_counts:
                    self.failure_counts[zone_id] = 0  # Reset counter
    
    def extract_zone_id(self, description: str) -> int:
        """Extrai zone ID da descrição do log"""
        import re
        match = re.search(r'Zone (\d+)', description)
        return int(match.group(1)) if match else -1
    
    def default_alert(self, zone_id: int, failure_count: int, message: str):
        """Alerta padrão (pode ser sobrescrito)"""
        print(f"\n⚠️  ALERTA CRÍTICO!")
        print(f"   Zona {zone_id} falhou {failure_count} vezes consecutivas")
        print(f"   Mensagem: {message}")
        print(f"   Recomendação: Verificar zona visualmente\n")


# ============================================================================
# EXEMPLO 6: Comparação de Múltiplos Métodos
# ============================================================================

def compare_alignment_methods(test_image: np.ndarray, 
                               golden_image: np.ndarray) -> Dict[str, float]:
    """
    Compara diferentes métodos de alinhamento e retorna scores.
    Útil para escolher o melhor método para suas imagens.
    """
    import sys
    sys.path.insert(0, './modules_production')
    import plate_alignment_inspection
    
    inspector = plate_alignment_inspection.module
    
    results = {}
    
    # Teste com ORB
    aligned_orb, _, msg_orb = inspector.align_images_orb(test_image, golden_image)
    results['ORB'] = {
        'success': aligned_orb is not None,
        'message': msg_orb,
        'time': 'rápido'
    }
    
    # Teste com ECC
    aligned_ecc, _, msg_ecc = inspector.align_images_ecc(test_image, golden_image)
    results['ECC'] = {
        'success': aligned_ecc is not None,
        'message': msg_ecc,
        'time': 'lento'
    }
    
    return results


# ============================================================================
# EXEMPLO 7: Função Helper para Análise Detalhada
# ============================================================================

def detailed_inspection_analysis(logs: List) -> Dict:
    """
    Analisa logs de inspeção e retorna estatísticas detalhadas.
    """
    analysis = {
        'total_zones': len(logs),
        'passed': 0,
        'failed': 0,
        'errors': 0,
        'similarities': [],
        'failed_zones': [],
        'error_zones': []
    }
    
    for log in logs:
        if 'ERROR' in log.description:
            analysis['errors'] += 1
            analysis['error_zones'].append(log.description)
        elif log.decision:
            analysis['passed'] += 1
            # Extrai % de similaridade
            import re
            match = re.search(r'Similarity: (\d+\.?\d*)%', log.description)
            if match:
                sim = float(match.group(1))
                analysis['similarities'].append(sim)
        else:
            analysis['failed'] += 1
            analysis['failed_zones'].append(log.description)
    
    # Calcula estatísticas
    if analysis['similarities']:
        analysis['avg_similarity'] = np.mean(analysis['similarities'])
        analysis['min_similarity'] = np.min(analysis['similarities'])
        analysis['max_similarity'] = np.max(analysis['similarities'])
    
    # Calcula taxa de aprovação
    analysis['pass_rate'] = (
        analysis['passed'] / analysis['total_zones'] * 100 
        if analysis['total_zones'] > 0 else 0
    )
    
    return analysis


# ============================================================================
# EXEMPLO 8: Integração com Banco de Dados (SQLAlchemy)
# ============================================================================

def save_inspection_result(inspection_data: Dict):
    """
    Exemplo de como salvar resultados no banco de dados
    (assumindo que você tem SQLAlchemy models).
    """
    from datetime import datetime
    
    # Pseudo-código (ajuste conforme sua estrutura de dados)
    """
    from open_aoi_core.models import InspectionResult, InspectionZoneResult
    from sqlalchemy.orm import Session
    from open_aoi_core.models import engine
    
    with Session(engine) as session:
        # Cria resultado de inspeção geral
        inspection = InspectionResult(
            camera_id=inspection_data['camera_id'],
            template_id=inspection_data['template_id'],
            timestamp=datetime.now(),
            overall_status='PASS' if inspection_data['pass_rate'] == 100 else 'FAIL',
            pass_rate=inspection_data['pass_rate'],
            avg_similarity=inspection_data.get('avg_similarity', 0)
        )
        session.add(inspection)
        session.flush()
        
        # Cria resultados por zona
        for zone_id, description in enumerate(inspection_data['failed_zones']):
            zone_result = InspectionZoneResult(
                inspection_id=inspection.id,
                zone_id=zone_id,
                status='FAIL',
                description=description
            )
            session.add(zone_result)
        
        session.commit()
        return inspection.id
    """


# ============================================================================
# MAIN: Demonstração
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Advanced Plate Alignment Inspection Examples")
    print("=" * 70)
    
    print("\n✓ Exemplos disponíveis:")
    print("  1. example_1_direct_usage() - Uso direto do handler")
    print("  2. PlateAlignmentWithHistory - Rastrear tendências")
    print("  3. PlateAlignmentWithMasking - Excluir áreas específicas")
    print("  4. PlateAlignmentMultiTemplate - Múltiplas golden images")
    print("  5. InspectionAlertSystem - Sistema de alertas")
    print("  6. compare_alignment_methods() - Comparar métodos")
    print("  7. detailed_inspection_analysis() - Análise detalhada")
    print("  8. save_inspection_result() - Salvar no BD")
    
    print("\nPara usar, importe os exemplos e chame as funções/classes.")
