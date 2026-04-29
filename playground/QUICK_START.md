# ⚡ Quick Start: Integração Alinhamento em 5 Minutos

## 📋 Checklist Rápido

### **FASE 1: Preparação** (2 minutos)

- [ ] Verificar que câmera está cadastrada no portal
  ```
  Portal → CONFIGURAÇÃO → Câmeras
  Confirmar: IP câmera correto, status online
  ```

- [ ] Ter uma imagem boa da placa (sem defeitos) para template
  ```
  Idealmente: boa iluminação, sem sombras, centralizador
  ```

### **FASE 2: Criar Defect Type** (1 minuto)

- [ ] Criar tipo de defeito
  ```
  Portal → CONFIGURAÇÃO → Inspection Handlers (seção esquerda)
  → Clique em "Create Defect Type"
  
  Preencha:
  - Título: "Placa Alignment Check"
  - Descrição: "Verifica alinhamento e defeitos da placa"
  → Save
  ```

### **FASE 3: Criar Inspection Handler** (1 minuto)

- [ ] Criar handler vinculado ao defect type
  ```
  Portal → CONFIGURAÇÃO → Inspection Handlers (continuando na mesma página)
  → Clique em "Create New Module"
  
  Preencha:
  - Título: "Plate Alignment Inspection"
  - Defect Type: Selecione "Placa Alignment Check" (criado acima)
  → Save
  ```

### **FASE 4: Upload Handler** (1 minuto)

- [ ] Fazer upload do arquivo
  ```
  Portal → CONFIGURAÇÃO → Inspection Handlers
  → Localize o module "Plate Alignment Inspection" na lista
  → Clique em "Edit" (ou no nome do module)
  → Clique em "Upload source"
  → Selecione: plate_alignment_inspection.py
  → Pronto! ✓
  ```

### **FASE 5: Criar Template** (1 minuto)

- [ ] Capturar golden image
  ```
  Portal → INSPEÇÃO → Templates
  Selecionar câmera → Capture image
  Review → Save como "PCI_Template_v1"
  ```

### **FASE 6: Definir Zonas** (2 minutos)

- [ ] Marcar componentes/áreas
  ```
  Portal → INSPEÇÃO → Templates → [Seu template]
  Clique na imagem e arraste para cada componente
  Ex: C1, C2, R1, IC1 (mínimo 2-3 zonas)
  ```

### **FASE 7: Criar Profile** (1 minuto)

- [ ] Criar inspection profile
  ```
  Portal → INSPEÇÃO → Profiles → Create
  
  Nome: "Quick_Test_v1"
  Template: [Seu template]
  Câmera: [Sua câmera]
  Handler: Plate Alignment Inspection
  
  Environment:
  SIMILARITY_THRESHOLD=0.85
  MAX_FEATURES=5000
  KEEP_PERCENT=0.2
  ALIGNMENT_METHOD=ORB
  ```

- [ ] Selecionar todas as zonas para o handler
- [ ] Save

### **FASE 8: Testar** (2 minutos)

- [ ] Teste no portal
  ```
  Portal → INSPEÇÃO → Inspeção em Tempo Real
  Selecionar profile: "Quick_Test_v1"
  Capture & Inspect
  
  Resultado esperado:
  ✓ Zone 1: PASS (Similarity: 92%)
  ✓ Zone 2: PASS (Similarity: 88%)
  ...
  ```

---

## 🔥 Troubleshooting Rápido

| Problema | Solução Rápida |
|----------|---|
| "Módulo não aparece após upload" | F5 no portal, limpar cache |
| "Alignment failed - Insufficient features" | ↑ `MAX_FEATURES=7000`, usar `ALIGNMENT_METHOD=ECC` |
| "Zonas falhando mesmo com imagem boa" | ↓ `SIMILARITY_THRESHOLD=0.75` |
| "Resultado mostra erro na zona" | Verificar se zona está dentro da imagem |
| "Demora muito para processar" | ↓ `MAX_FEATURES=3000`, usar `ALIGNMENT_METHOD=ORB` |

---

## 📊 Resultado Esperado

Quando funcionar, você vai ver no portal:

```
INSPEÇÃO RESULTADO:
═══════════════════════════════════════════

Template: PCI_Template_v1
Câmera: Camera_001
Horário: 2026-04-29 10:35:42

RESULTADOS POR ZONA:
────────────────────────────────────────────
✓ C1 (Capacitor):      PASS (Similarity: 91.5%)
✓ C2 (Capacitor):      PASS (Similarity: 89.2%)  
✗ R1 (Resistor):       FAIL (Similarity: 72.1%)  ← DEFEITO DETECTADO!
✓ IC1 (Chip):          PASS (Similarity: 93.8%)

RESUMO:
────────────────────────────────────────────
Aprovado:    3/4 zonas (75%)
Status: FAIL ❌

RECOMENDAÇÃO:
Verificar a zona "R1 (Resistor)" - Possível defeito de solda ou componente mal posicionado
```

---

## 🎯 Próximas Customizações (Opcional)

Após validar que funciona, você pode:

1. **Ajustar SIMILARITY_THRESHOLD**
   - Se muitos falsos positivos: ↓ para 0.80
   - Se muitos falsos negativos: ↑ para 0.90

2. **Dividir zonas grandes**
   - Uma zona muito grande = menos precisão
   - Melhor: 4-6 zonas pequenas do que 1 grande

3. **Teste com método ECC**
   - Se ORB não funciona bem, tente:
   ```
   ALIGNMENT_METHOD=ECC
   MAX_FEATURES=5000
   ```

4. **Implementar histórico**
   - Use arquivo `advanced_examples.py`
   - Classe: `PlateAlignmentWithHistory`

---

## 📁 Arquivos Criados para Você

```
✓ plate_alignment_inspection.py    ← Handler (upload no portal)
✓ test_plate_alignment.ipynb        ← Testes locais (executar no Jupyter)
✓ GUIA_INTEGRACAO_ALINHAMENTO.md   ← Guia completo
✓ advanced_examples.py              ← Exemplos avançados
✓ QUICK_START.md                    ← Este arquivo
```

---

## ⏱️ Tempo Total

- Preparação: 2 min
- Setup (Defect Type + Handler): 2 min
- Upload: 1 min
- Template + Zones: 3 min
- Profile: 1 min
- Testes: 5-10 min
- Ajustes: 5-10 min

**Total: ~20-30 minutos para estar funcionando!**

---

## 🚀 Começar Agora!

1. Abra o portal: `http://127.0.0.1:10006`
2. Vá para: `CONFIGURAÇÃO → Inspection Handlers`
3. Siga o Checklist acima (8 fases = ~15 minutos)
4. Celebrar! 🎉

---

**Criado:** Abril 2026
**Status:** Pronto para uso em produção
