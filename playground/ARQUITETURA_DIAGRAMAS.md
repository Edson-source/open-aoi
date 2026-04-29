# 🏗️ Arquitetura da Integração - Diagramas

## 1️⃣ Fluxo Geral (Alto Nível)

```
┌─────────────────────────────────────────────────────────────────┐
│                         PORTAL WEB UI                           │
│  (http://127.0.0.1:10006)                                       │
│  - Cadastro de câmeras                                          │
│  - Capture de golden images (templates)                         │
│  - Definição de inspection zones                                │
│  - Criação de inspection profiles                               │
│  - Visualização de resultados                                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ HTTP/REST API
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MEDIADOR (Service)                           │
│  service_mediator.py                                            │
│  - Orquestra fluxo de inspeção                                  │
│  - Captura imagem da câmera                                     │
│  - Busca golden image do storage                                │
│  - Dispara handlers de inspeção                                 │
└──────┬──────────────┬──────────────┬─────────────────────────────┘
       │              │              │
   ROS2 Service Calls (Async)
       │              │              │
       ▼              ▼              ▼
┌────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  Image     │  │  Product          │  │  Inspection      │
│Acquisition │  │ Identification    │  │  Execution       │
│  Service   │  │   Service         │  │   Service        │
│            │  │                   │  │                  │
│ Câmera IP  │  │ Detecção de       │  │ Executa handlers │
│ Envia ROS  │  │ código de barras  │  │ Python modules   │
│ Message    │  │                   │  │                  │
└────────────┘  └───────────────────┘  └──────────────────┘
                                               │
                                               │ test_image
                                               │ template_image
                                               │ inspection_handler
                                               │
                                               ▼
                        ┌──────────────────────────────────┐
                        │  INSPECTION HANDLER              │
                        │  (Python Module)                 │
                        │                                  │
                        │ plate_alignment_inspection.py    │
                        │                                  │
                        │ 1. Alinha imagens (ORB/ECC)      │
                        │ 2. Compara zonas                 │
                        │ 3. Retorna logs                  │
                        │    - Zone 1: PASS/FAIL           │
                        │    - Zone 2: PASS/FAIL           │
                        │    - ...                         │
                        └──────────────────────────────────┘
                                   │
                                   │ InspectionLog[]
                                   ▼
                        ┌──────────────────────────────────┐
                        │  Mediador                        │
                        │  Processa Logs                   │
                        │  Salva no Banco de Dados         │
                        │  Retorna ao Portal               │
                        └──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PORTAL - RESULTADO                           │
│  ✓ Zone 1: PASS (92%)                                           │
│  ✓ Zone 2: PASS (88%)                                           │
│  ✗ Zone 3: FAIL (72%)  ← DEFEITO DETECTADO!                     │
│  ✓ Zone 4: PASS (93%)                                           │
│                                                                  │
│  Status Overall: FAIL                                           │
│  Aprovação: 3/4 (75%)                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ Fluxo Detalhado de Inspeção

```
START
  │
  ├─► 1. Mediador recebe request de inspeção
  │       └─ camera_id ou io_pin
  │
  ├─► 2. Captura imagem da câmera
  │       Camera Service → sensor_msgs/Image (RGB)
  │
  ├─► 3. Identifica produto
  │       Product ID Service → identification_code
  │
  ├─► 4. Busca Inspection Profile
  │       DB Query → InspectionProfile
  │       ├─ template
  │       ├─ inspection_zones
  │       └─ inspection_handlers
  │
  ├─► 5. Carrega Golden Image
  │       template.materialize_image()
  │       │
  │       ├─► Arquivo Minio (storage de blobs)
  │       │
  │       ├─► PIL.Image
  │       │
  │       ├─► numpy.array (BGR)
  │       │
  │       └─► sensor_msgs/Image (ROS Message)
  │
  ├─► 6. Dispara Inspection Execution Service
  │       │
  │       │ InspectionExecutionTrigger.Request
  │       ├─ test_image (sensor_msgs/Image)
  │       ├─ template_image (sensor_msgs/Image)  ◄─── GOLDEN IMAGE
  │       ├─ inspection_handler (str - código Python)
  │       ├─ inspection_targets (List[InspectionTarget])
  │       └─ environment (str - parâmetros)
  │
  ├─► 7. Serviço executa handler
  │       │
  │       ├─► imgmsg_to_cv2(test_image)
  │       │    └─ numpy.ndarray (RGB) - imagem capturada
  │       │
  │       ├─► imgmsg_to_cv2(template_image)
  │       │    └─ numpy.ndarray (BGR) - golden image
  │       │
  │       ├─► handler.process()
  │       │    │
  │       │    ├─► ALINHAMENTO (ORB/ECC)
  │       │    │    align_images_orb() ou align_images_ecc()
  │       │    │    └─ Retorna: aligned_image, homography_matrix
  │       │    │
  │       │    ├─► PARA CADA ZONA
  │       │    │    ├─ Cut zona de aligned_image
  │       │    │    ├─ Cut zona de golden_image
  │       │    │    ├─ compute_zone_similarity()
  │       │    │    │   └─ Histograma, comparação
  │       │    │    │
  │       │    │    ├─ Compara com SIMILARITY_THRESHOLD
  │       │    │    │
  │       │    │    └─ Retorna InspectionLog
  │       │    │       ├─ description: "Zone X: PASS/FAIL (Y%)"
  │       │    │       └─ decision: True/False
  │       │    │
  │       │    └─ Retorna List[InspectionLog]
  │       │
  │       └─► Mediador recebe response
  │
  ├─► 8. Processa logs e salva no BD
  │       │
  │       ├─ Create InspectionResult record
  │       ├─ Create InspectionZoneResult para cada zona
  │       └─ Commit no database
  │
  └─► 9. Retorna ao Portal
          Portal exibe resultados visual
          ✓ Zona aprovada
          ✗ Zona com defeito

END
```

---

## 3️⃣ Estrutura de Dados - Flow

```
┌──────────────────────────────────┐
│  Portal Form (Criar Profile)     │
│  ├─ camera: Camera               │
│  ├─ template: Template           │
│  ├─ handler: "Plate Alignment"   │
│  └─ environment:                 │
│     SIMILARITY_THRESHOLD=0.85    │
│     MAX_FEATURES=5000            │
│     KEEP_PERCENT=0.2             │
│     ALIGNMENT_METHOD=ORB         │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  InspectionProfile (Database)                │
│  ├─ id: UUID                                 │
│  ├─ camera_id: UUID → Camera                 │
│  ├─ template_id: UUID → Template             │
│  ├─ environment: JSON/String                 │
│  └─ inspection_handler_list:                 │
│     [                                        │
│       {                                      │
│         id: UUID,                            │
│         source: "# código Python",           │
│         targets: [InspectionZone, ...]       │
│       }                                      │
│     ]                                        │
└──────────────────────────────────────────────┘
         │
         ├─► camera.ip_address → capture image
         │
         ├─► template.materialize_image() → golden_img
         │
         └─► Dispara para handler

┌──────────────────────────────────────────────┐
│  Handler Process Input                       │
│  ├─ environment: dict                        │
│  ├─ test_image: ndarray (RGB)                │
│  ├─ template_image: ndarray (BGR)            │
│  └─ inspection_zone_list: [InspectionZone]   │
└──────────────────────────────────────────────┘
         │
         ▼ (align_images())
┌──────────────────────────────────────────────┐
│  Alinhamento                                 │
│  ├─ detect_keypoints() → ORB                 │
│  ├─ match_descriptors()                      │
│  ├─ findHomography() → H (3x3 matrix)        │
│  └─ warpPerspective() → aligned_image        │
└──────────────────────────────────────────────┘
         │
         ├─► PARA CADA ZONA
         │   ├─ cut_inspection_zone()
         │   ├─ compute_zone_similarity()
         │   │  ├─ calcHist()
         │   │  └─ compareHist() → [0.0, 1.0]
         │   │
         │   ├─ compara com THRESHOLD
         │   │
         │   └─ InspectionLog(decision=PASS/FAIL)
         │
         ▼
┌──────────────────────────────────────────────┐
│  Handler Output                              │
│  [                                           │
│    InspectionLog(                            │
│      description="Zone 1: PASS (92.5%)",    │
│      decision=True                           │
│    ),                                        │
│    InspectionLog(                            │
│      description="Zone 2: FAIL (72.1%)",    │
│      decision=False                          │
│    ),                                        │
│    ...                                       │
│  ]                                           │
└──────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  Portal - Resultado Final                    │
│                                              │
│  ✓ Zone 1: PASS (92.5%)                      │
│  ✗ Zone 2: FAIL (72.1%)  ← DEFEITO!          │
│  ✓ Zone 3: PASS (88.3%)                      │
│  ✓ Zone 4: PASS (91.7%)                      │
│                                              │
│  Resultado: 3/4 (75%)                        │
│  Status: FALHOU ❌                            │
└──────────────────────────────────────────────┘
```

---

## 4️⃣ Componentes Principais

```
┌─────────────────────────────────────────┐
│          PLATE ALIGNMENT MODULE         │
│  (plate_alignment_inspection.py)        │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ ORB Alignment                   │   │
│  │ align_images_orb()              │   │
│  │ ├─ Fast (real-time capable)     │   │
│  │ ├─ Feature-based (robust)       │   │
│  │ └─ Returns: aligned_img, H      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ ECC Alignment                   │   │
│  │ align_images_ecc()              │   │
│  │ ├─ More robust (small rotations)│   │
│  │ ├─ Slower                       │   │
│  │ └─ Returns: aligned_img, W      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Zone Similarity                 │   │
│  │ compute_zone_similarity()       │   │
│  │ ├─ Histogram correlation        │   │
│  │ ├─ Robust to lighting changes   │   │
│  │ └─ Returns: [0.0 ... 1.0]       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Main Process Loop               │   │
│  │ process(env, test, template,    │   │
│  │         zones)                  │   │
│  │ ├─ 1. Align images              │   │
│  │ ├─ 2. For each zone:            │   │
│  │ │   ├─ Extract chunks           │   │
│  │ │   ├─ Compare similarity       │   │
│  │ │   └─ Generate log             │   │
│  │ └─ Returns: [InspectionLog]     │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## 5️⃣ Configuração de Parâmetros

```
┌─────────────────────────────────────────────────────────────────┐
│                   ENVIRONMENT VARIABLES                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIMILARITY_THRESHOLD                                            │
│  │                                                               │
│  ├─ Range: 0.0 ... 1.0 (0% ... 100%)                            │
│  │                                                               │
│  ├─ Default: 0.85 (85%)                                         │
│  │                                                               │
│  ├─ Comportamento:                                              │
│  │   0.95 ├─► MUY RIGUROSO (poucos falsos negativos)            │
│  │   0.85 ├─► BALANCEADO (recomendado)                          │
│  │   0.75 ├─► TOLERANTE (mais falsos positivos)                 │
│  │   0.65 ├─► MUITO TOLERANTE (detecta apenas grandes defeitos) │
│  │                                                               │
│  │ Se muitos falsos positivos  → aumentar para 0.90             │
│  │ Se muitos falsos negativos  → diminuir para 0.80             │
│  │                                                               │
│  └─ Impact: ALTO (decide PASS/FAIL)                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MAX_FEATURES                                                    │
│  │                                                               │
│  ├─ Range: 100 ... 10000                                        │
│  │                                                               │
│  ├─ Default: 5000                                               │
│  │                                                               │
│  ├─ Comportamento:                                              │
│  │   10000 ├─► Mais features = Melhor alinhamento (MAS LENTO)   │
│  │   5000  ├─► BALANCEADO (recomendado)                         │
│  │   3000  ├─► Rápido mas menos preciso                         │
│  │   1000  ├─► Muito rápido mas pode falhar em rotação         │
│  │                                                               │
│  │ Se "Insufficient features" → aumentar para 7000              │
│  │ Se lento demais              → diminuir para 3000            │
│  │                                                               │
│  └─ Impact: MÉDIO (melhora robustez)                            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  KEEP_PERCENT                                                    │
│  │                                                               │
│  ├─ Range: 0.01 ... 0.5 (1% ... 50%)                            │
│  │                                                               │
│  ├─ Default: 0.2 (20%)                                          │
│  │                                                               │
│  ├─ Comportamento:                                              │
│  │   0.5  ├─► Aceita 50% dos matches (menos rigoroso)           │
│  │   0.2  ├─► BALANCEADO (recomendado)                          │
│  │   0.1  ├─► Apenas 10% dos melhores matches (muito rigoroso)  │
│  │                                                               │
│  │ Aumentar se: Alinhamento falhando                            │
│  │ Diminuir se: Alinhamento instável                            │
│  │                                                               │
│  └─ Impact: BAIXO (afina alinhamento)                           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ALIGNMENT_METHOD                                                │
│  │                                                               │
│  ├─ Valores: "ORB" ou "ECC"                                     │
│  │                                                               │
│  ├─ Default: "ORB"                                              │
│  │                                                               │
│  ├─ Comparação:                                                 │
│  │                                                               │
│  │  ORB:                          ECC:                           │
│  │  ├─ Rápido ✓                   ├─ Mais lento ✗               │
│  │  ├─ Feature-based              ├─ Intensity-based            │
│  │  ├─ Bom para rotação ✓         ├─ Muito bom para rotação     │
│  │  ├─ Recomendado padrão ✓       ├─ Para casos difíceis        │
│  │  └─ Menos preciso ⚠            └─ Mais preciso ✓             │
│  │                                                               │
│  │ Usar ORB se: Produção normal com boa iluminação              │
│  │ Usar ECC se: Muita rotação ou sombras                        │
│  │                                                               │
│  └─ Impact: ALTO (muda completamente o algoritmo)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6️⃣ Predefinições Recomendadas

```
┌──────────────────────────────────────────┐
│ CENÁRIO 1: Manufatura Normal             │
│ (Default - comece por aqui)              │
├──────────────────────────────────────────┤
│ SIMILARITY_THRESHOLD=0.85                │
│ MAX_FEATURES=5000                        │
│ KEEP_PERCENT=0.2                         │
│ ALIGNMENT_METHOD=ORB                     │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ CENÁRIO 2: Alta Precisão / Zero Defeitos │
│ (Produtos premium)                       │
├──────────────────────────────────────────┤
│ SIMILARITY_THRESHOLD=0.90                │
│ MAX_FEATURES=7000                        │
│ KEEP_PERCENT=0.1                         │
│ ALIGNMENT_METHOD=ECC                     │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ CENÁRIO 3: Rápido / Detecta Óbvios       │
│ (Alta throughput, tolerância)            │
├──────────────────────────────────────────┤
│ SIMILARITY_THRESHOLD=0.75                │
│ MAX_FEATURES=3000                        │
│ KEEP_PERCENT=0.3                         │
│ ALIGNMENT_METHOD=ORB                     │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ CENÁRIO 4: Imagens Rotacionadas          │
│ (Placas não centralizadas)               │
├──────────────────────────────────────────┤
│ SIMILARITY_THRESHOLD=0.85                │
│ MAX_FEATURES=7000                        │
│ KEEP_PERCENT=0.2                         │
│ ALIGNMENT_METHOD=ECC                     │
└──────────────────────────────────────────┘
```

---

**Criado:** Abril 2026
**Versão:** 1.0
