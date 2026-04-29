# 🎯 Guia de Integração: Alinhamento de Placas AOI

## Visão Geral

Este guia mostra como integrar o handler de alinhamento (`plate_alignment_inspection.py`) no seu sistema de inspeção, permitindo que o Open AOI:

1. ✅ Alinhe automaticamente a imagem capturada com a golden image
2. ✅ Compara zonas de inspeção com alta precisão
3. ✅ Retorne ao portal exatamente quais componentes/áreas falharam
4. ✅ Funcione com rotações e pequenas deformações

---

## 📋 Sumário de Passos

| Etapa | Descrição | Arquivo |
|-------|-----------|---------|
| 1️⃣ | Fazer upload do handler no portal | `plate_alignment_inspection.py` |
| 2️⃣ | Criar um Inspection Profile com o handler | Portal Web UI |
| 3️⃣ | Testar com imagens reais | `test_plate_alignment.ipynb` |
| 4️⃣ | Configurar parâmetros de threshold | Environment no Portal |
| 5️⃣ | Validar resultados e retorno de falhas | Inspeção em Tempo Real |

---

## 🚀 Passo 1: Upload do Handler no Portal

### 1.1 Acessar a Seção de Módulos

```
1. Abra o portal: http://127.0.0.1:10006
2. Login com usuário Administrator
3. Navegue para: CONFIGURAÇÃO → Módulos
```

### 1.2 Upload do Arquivo

```
1. Clique em "Upload New Module"
2. Selecione o arquivo: plate_alignment_inspection.py
3. O sistema vai extrair a documentação automaticamente
4. Clique em "Save"
```

**Resultado esperado:**
- ✅ Módulo listado como "Plate Alignment Inspection"
- ✅ Documentação visível com parâmetros

---

## 🎨 Passo 2: Criar Inspection Profile

### 2.1 Preparar a Golden Image (Template)

```
1. No portal: INSPEÇÃO → Templates
2. Selecione a câmera previamente cadastrada
3. Clique "Capture image" (capture uma boa imagem da placa sem defeitos)
4. Clique "Save" → atribua um nome significativo
   Ex: "PCI_Standard_v1.0"
```

### 2.2 Definir Zonas de Inspeção

```
1. Clique no template recém criado
2. A imagem abre no "Inspection Zone Editor"
3. Para cada componente/área que deseja monitorar:
   - Clique e arraste para criar um retângulo
   - Salve a zona (com um nome descritivo)
   
   Exemplo de zonas:
   ✓ Zone 1: "Capacitor_C1"
   ✓ Zone 2: "Capacitor_C2"
   ✓ Zone 3: "IC_Chip"
   ✓ Zone 4: "Resistor_R1"
```

### 2.3 Criar o Inspection Profile

```
1. Navegue para: INSPEÇÃO → Profiles
2. Clique "Create Profile"
3. Configure:
   - Nome: "Plate_Alignment_Check_v1"
   - Template: Selecione o template criado em 2.1
   - Câmera: Selecione a câmera
   - Status: Ativo
4. Clique "Next" para adicionar handlers
```

### 2.4 Adicionar o Handler ao Profile

```
1. Clique "Add Inspection Handler"
2. Selecione: "Plate Alignment Inspection"
3. Configure o Environment (parâmetros):
   
   SIMILARITY_THRESHOLD=0.85
   MAX_FEATURES=5000
   KEEP_PERCENT=0.2
   ALIGNMENT_METHOD=ORB

4. Selecione as Inspection Zones que este handler vai usar
   (normalmente todas)
5. Clique "Save"
6. Clique "Save Profile"
```

---

## 🔧 Passo 3: Testes Iniciais

### 3.1 Testar Localmente (Notebook)

```bash
# No seu ambiente Python, abra:
open-aoi/playground/inspection_development/test_plate_alignment.ipynb

# Execute as células para validar:
- Alinhamento com rotação
- Detecção de componentes faltando
- Comparação com diferentes thresholds
```

### 3.2 Testar via Portal

```
1. Navegue para: INSPEÇÃO → Inspeção em Tempo Real
2. Selecione o profile criado: "Plate_Alignment_Check_v1"
3. Clique "Capture & Inspect"
4. Resultado deve mostrar:
   ✓ Zonas que passaram
   ✗ Zonas que falharam com % de similaridade
```

---

## ⚙️ Passo 4: Configurar Parâmetros

### 4.1 Entender os Parâmetros

| Parâmetro | Range | Padrão | Função |
|-----------|-------|--------|--------|
| **SIMILARITY_THRESHOLD** | 0.0-1.0 | 0.85 | Quanto da imagem precisa ser idêntica (85% = muito rigoroso) |
| **MAX_FEATURES** | 100-10000 | 5000 | Mais features = melhor alinhamento mas mais lento |
| **KEEP_PERCENT** | 0.01-0.5 | 0.2 | % dos melhores matches para usar (0.2 = 20%) |
| **ALIGNMENT_METHOD** | ORB / ECC | ORB | ORB = rápido, ECC = mais preciso |

### 4.2 Recomendações por Caso de Uso

#### 🎯 **Caso 1: Detecção Rigorosa (Alta Qualidade)**
```
SIMILARITY_THRESHOLD=0.90
MAX_FEATURES=7000
KEEP_PERCENT=0.1
ALIGNMENT_METHOD=ECC
```
*Uso: Placas de produtos premium, zero defeitos permitido*

#### 🏭 **Caso 2: Manufatura Normal (Padrão)**
```
SIMILARITY_THRESHOLD=0.85
MAX_FEATURES=5000
KEEP_PERCENT=0.2
ALIGNMENT_METHOD=ORB
```
*Uso: Produção em série normal*

#### 🔄 **Caso 3: Tolerância Alta (Rápido)**
```
SIMILARITY_THRESHOLD=0.75
MAX_FEATURES=3000
KEEP_PERCENT=0.3
ALIGNMENT_METHOD=ORB
```
*Uso: Detecção apenas de falhas grosseiras/óbvias*

---

## 📊 Passo 5: Validar Resultados

### 5.1 Estrutura de Resposta

O handler retorna logs estruturados:

```
✓ Zone 1: PASS (Similarity: 92.5%, Threshold: 85.0%)
✓ Zone 2: PASS (Similarity: 88.3%, Threshold: 85.0%)
✗ Zone 3: FAIL (Similarity: 72.1%, Threshold: 85.0%)
✓ Zone 4: PASS (Similarity: 91.7%, Threshold: 85.0%)

Resultado: 3/4 zonas aprovadas
```

### 5.2 Interpretar Falhas

**Se uma zona falha, significa:**
- A imagem foi alinhada ✓
- Mas a similaridade está abaixo do threshold
- Possíveis causas:
  - Componente ausente
  - Componente posicionado incorretamente
  - Solda defeituosa
  - Iluminação muito diferente

### 5.3 Solução de Problemas

#### ❌ "Alignment failed - Insufficient features"

**Causa:** Imagem muito lisa ou uniforme
**Solução:**
- Aumentar `MAX_FEATURES` para 7000+
- Usar método ECC: `ALIGNMENT_METHOD=ECC`
- Verificar iluminação da câmera

#### ❌ "Zones failing mesmo em imagem boa"

**Causa:** SIMILARITY_THRESHOLD muito alto
**Solução:**
- Reduzir para 0.80 ou 0.75
- Certificar que golden image tem boa qualidade

#### ❌ "Falso positivo - componente faltando não detectado"

**Causa:** Threshold muito baixo ou zona muito grande
**Solução:**
- Aumentar SIMILARITY_THRESHOLD para 0.90
- Dividir zonas grandes em menores
- Melhorar iluminação para contraste melhor

---

## 🔗 Fluxo Completo de Integração

```
┌──────────────────────────────────┐
│ 1. Upload handler no portal      │
│    (plate_alignment_inspection)  │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 2. Capture Golden Image          │
│    (Template na câmera real)     │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 3. Define Inspection Zones       │
│    (Marcar componentes na imagem)│
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 4. Create Inspection Profile     │
│    (Link: template + handler)    │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 5. Test Localmente (Notebook)    │
│    (Validar com imagens variadas)│
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 6. Inspeção em Tempo Real        │
│    (Porta: resultado por zona)   │
└──────────────────────────────────┘
```

---

## 📁 Arquivos Envolvidos

### Arquivos que você vai usar/modificar:

```
open-aoi/
├── playground/inspection_development/
│   ├── modules_production/
│   │   └── plate_alignment_inspection.py    ← Handler (UPLOAD NO PORTAL)
│   └── test_plate_alignment.ipynb            ← Testes locais
├── src/open_aoi_portal/                      ← Portal web (não precisa modificar)
└── src/open_aoi_services/                    ← Serviços (não precisa modificar)
```

### Arquivos de referência (apenas leitura):

```
src/open_aoi_services/
├── service_mediator.py                   ← Orquestra inspeção
├── service_inspection_execution.py       ← Executa handlers
└── service_product_identification.py     ← align_images() implementado aqui
```

---

## ✅ Checklist de Implementação

- [ ] Upload handler `plate_alignment_inspection.py` no portal
- [ ] Golden image capturada e salva (template)
- [ ] Zonas de inspeção definidas (mínimo 2-3 áreas)
- [ ] Inspection Profile criado e ativo
- [ ] Handler associado ao profile com parâmetros configurados
- [ ] Teste local executado (notebook) com sucesso
- [ ] Inspeção em tempo real testada
- [ ] Portal mostra resultados por zona (pass/fail)
- [ ] Thresholds ajustados conforme necessário

---

## 🎓 Próximos Passos

### Melhorias Futuras:

1. **Visualização no Portal**
   - Mostrar imagem alinhada lado-a-lado com golden
   - Destacar em vermelho as áreas que falharam
   - Heatmap de similaridade por zona

2. **Histórico de Inspeções**
   - Rastrear % de similaridade ao longo do tempo
   - Detectar degradação gradual de componentes

3. **Alertas**
   - Notificar quando zona específica falha 3x seguidas
   - Sugerir manutenção preventiva

4. **Múltiplos Métodos**
   - Template Matching (para componentes pequenos)
   - Feature Detection com diferentes extractors
   - Deep Learning (CNN) para defeitos mais complexos

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs em: `/aoi-ros2` container
2. Execute o notebook de teste com suas imagens reais
3. Ajuste SIMILARITY_THRESHOLD incrementalmente
4. Verifique iluminação da câmera

---

**Criado em:** Abril 2026
**Versão:** 1.0
