# 🧪 Teste Prático do Plate Alignment Inspector

## ✨ Objetivo

Testar o módulo `Plate alignment inspection` direto no portal, de forma prática e rápida.

---

## 📋 Pré-Requisitos

- ✅ Docker rodando: `docker compose --profile full up -d --build`
- ✅ Portal aberto: `http://127.0.0.1:10006`
- ✅ Câmera cadastrada e online
- ✅ Módulo aparece em: `CONFIGURAÇÃO → Inspection Handlers`

---

## 🚀 TESTE RÁPIDO (5 minutos)

### **PASSO 1: Capture a Golden Image (Template)**

```
1. Abra o portal: http://127.0.0.1:10006
2. Navegue para: INSPEÇÃO → Templates
3. Clique em: "Create Template"
4. Preencha:
   - Título: "Test_Template_v1"
   - Câmera: Selecione sua câmera
5. Clique em "Capture image"
   └─ Coloque uma placa BOA na câmera (sem defeitos!)
   └─ A imagem será capturada
6. Clique em "Save"
```

✅ **Resultado esperado:** Template salvo com a imagem golden

---

### **PASSO 2: Defina Inspection Zones**

```
1. Clique no template: "Test_Template_v1"
2. A imagem abre em um editor
3. Clique e ARRASTE para criar retângulos sobre:
   - Componentes diferentes
   - Áreas onde espera defeitos
   
   Crie pelo menos 3 zonas:
   Zone 1: "Component_A"  (parte esquerda)
   Zone 2: "Component_B"  (parte central)
   Zone 3: "Component_C"  (parte direita)
   
4. Clique "Save" para cada zona
```

✅ **Resultado esperado:** 3+ zonas definidas

---

### **PASSO 3: Crie um Inspection Profile**

```
1. Navegue para: INSPEÇÃO → Profiles
2. Clique em: "Create Profile"
3. Preencha:
   - Título: "Test_Profile_v1"
   - Câmera: Selecione sua câmera
   - Template: "Test_Template_v1"
   - Status: Ativo
4. Clique em "Next"
```

---

### **PASSO 4: Adicione o Handler**

```
1. Na página de Profile, clique em: "Add Inspection Handler"
2. Selecione: "Plate alignment inspection"
3. Configure o Environment:

   SIMILARITY_THRESHOLD=0.85
   MAX_FEATURES=5000
   KEEP_PERCENT=0.2
   ALIGNMENT_METHOD=ORB

4. Selecione as Inspection Zones:
   ☑ Component_A
   ☑ Component_B
   ☑ Component_C
   
5. Clique em "Save"
6. Clique em "Save Profile"
```

✅ **Profile criado e pronto!**

---

### **PASSO 5: Execute o Teste**

```
1. Navegue para: INSPEÇÃO → Inspeção em Tempo Real
2. Selecione o Profile: "Test_Profile_v1"
3. Clique em "Capture & Inspect"
4. Aguarde 5-10 segundos...
5. Resultado aparecerá na tela
```

---

## 📊 INTERPRETAR RESULTADOS

### **Resultado Esperado (Imagem Boa = Imagem Golden):**

```
✅ INSPEÇÃO RESULTADO
════════════════════════════════════════

Template: Test_Template_v1
Câmera: [Sua Câmera]
Horário: 2026-04-29 14:35:42

RESULTADO POR ZONA:
────────────────────────────────────────
✓ Component_A:  PASS (Similarity: 92.5%)
✓ Component_B:  PASS (Similarity: 88.3%)
✓ Component_C:  PASS (Similarity: 91.7%)

RESUMO:
────────────────────────────────────────
Aprovado:    3/3 zonas (100%)
Status:      PASS ✅

Tempo de inspeção: 2.3 segundos
```

### **Significado:**
- ✅ **PASS**: Zona aprovada (similaridade ≥ 85%)
- ❌ **FAIL**: Zona reprovada (similaridade < 85%)
- 📊 **Similarity %**: Quanto a zona é parecida com o template

---

## 🧪 TESTE COM DEFEITO SIMULADO

### **Para validar detecção de defeitos:**

```
1. Coloque a placa com DEFEITO na câmera
   Exemplos:
   - Componente faltando
   - Componente virado
   - Componente solto
   - Soldadura ruim em uma área
   
2. Volte para: INSPEÇÃO → Inspeção em Tempo Real
3. Clique em "Capture & Inspect" novamente
4. Resultado deve mostrar:
```

### **Resultado Esperado (Com Defeito):**

```
⚠️  INSPEÇÃO RESULTADO
════════════════════════════════════════

Template: Test_Template_v1
Câmera: [Sua Câmera]

RESULTADO POR ZONA:
────────────────────────────────────────
✓ Component_A:  PASS (Similarity: 91.2%)
✗ Component_B:  FAIL (Similarity: 62.1%)  ← DEFEITO AQUI!
✓ Component_C:  PASS (Similarity: 89.8%)

RESUMO:
────────────────────────────────────────
Aprovado:    2/3 zonas (66.7%)
Status:      FAIL ❌

COMPONENTE COM DEFEITO:
- Component_B (Similarity 62.1% vs Threshold 85%)
```

✅ **Isto significa que o módulo detectou corretamente!**

---

## 🔍 TESTE DE PARÂMETROS

### **Experimento 1: Mudar SIMILARITY_THRESHOLD**

```
Objetivo: Ver como o threshold afeta resultados

1. Edite o profile: "Test_Profile_v1"
2. Atualize o handler com:

   Cenário 1: SIMILARITY_THRESHOLD=0.95 (muito rigoroso)
   Cenário 2: SIMILARITY_THRESHOLD=0.85 (padrão)
   Cenário 3: SIMILARITY_THRESHOLD=0.75 (tolerante)
   
3. Para cada cenário, capture novamente
4. Veja como resultado muda:
   - 0.95: Mais zonas falham
   - 0.85: Balanceado
   - 0.75: Mais zonas passam
```

### **Experimento 2: Comparar Métodos (ORB vs ECC)**

```
1. Capture a golden image com rotação leve (2-3°)
2. Depois capture com rotação maior (5-10°)
3. Teste com:
   
   Teste 1: ALIGNMENT_METHOD=ORB
   Resultado: Trabalha bem com pequenas rotações
   
   Teste 2: ALIGNMENT_METHOD=ECC
   Resultado: Mais robusto com rotações maiores
```

---

## 📱 TESTE COMPLETO (15 minutos)

### **Checklist:**

- [ ] **SETUP (5 min)**
  - [ ] Template criado
  - [ ] 3+ zonas definidas
  - [ ] Profile criado
  - [ ] Handler associado

- [ ] **TESTE POSITIVO (3 min)**
  - [ ] Imagem boa na câmera
  - [ ] Clique "Capture & Inspect"
  - [ ] Resultado mostra ✅ PASS

- [ ] **TESTE NEGATIVO (3 min)**
  - [ ] Coloque defeito na placa
  - [ ] Clique "Capture & Inspect" novamente
  - [ ] Resultado mostra ❌ FAIL na zona com defeito

- [ ] **TESTE DE PARÂMETROS (4 min)**
  - [ ] Mude SIMILARITY_THRESHOLD
  - [ ] Veja mudança nos resultados
  - [ ] Teste ORB vs ECC

---

## 🎯 Esperado vs Observado

| Cenário | Esperado | Se Não Funcionar |
|---------|----------|------------------|
| Imagem Boa | ✅ PASS 100% | Verificar iluminação da câmera |
| Componente Faltando | ❌ FAIL naquela zona | Verificar zona abrange o componente |
| Rotação Leve (2°) | ✅ PASS mesmo assim | ↑ MAX_FEATURES para 7000 |
| Rotação Grande (10°) | ❌ Pode falhar com ORB | Mudar para ALIGNMENT_METHOD=ECC |
| Threshold 0.95 | Mais rigoroso | Aumenta FAIL rate |
| Threshold 0.75 | Mais tolerante | Diminui FAIL rate |

---

## 🚨 Se Der Erro

### **Erro: "Alignment failed"**
```
Solução 1: ↑ MAX_FEATURES=7000
Solução 2: Melhorar iluminação da câmera
Solução 3: Mudar para ALIGNMENT_METHOD=ECC
```

### **Erro: "Inspection handler invalid"**
```
Solução: Verifique se o módulo está 🟢 (verde) em:
CONFIGURAÇÃO → Inspection Handlers
```

### **Erro: "Timeout"**
```
Solução 1: ↓ MAX_FEATURES=3000 (mais rápido)
Solução 2: Esperar mais tempo (ECC é lento)
```

### **Resultado sempre PASS (mesmo com defeito)**
```
Solução: ↑ SIMILARITY_THRESHOLD=0.90
```

### **Resultado sempre FAIL (mesmo com imagem boa)**
```
Solução 1: ↓ SIMILARITY_THRESHOLD=0.80
Solução 2: Verificar se golden image é de boa qualidade
```

---

## 📊 Entender a Saída

```
✓ Component_A: PASS (Similarity: 92.5%)
│  │           │     │           │
│  │           │     │           └─ % de similaridade (0-100%)
│  │           │     └─ Resultado
│  │           └─ Status geral da zona
│  └─ Nome da zona
└─ ✅ = Passou (Similarity ≥ Threshold)

❌ Component_B: FAIL (Similarity: 62.1%)
└─ ❌ = Falhou (Similarity < Threshold)
   Significa que 62.1% < 85% (threshold)
   Logo, FALHOU!
```

---

## 🎓 Próximos Passos

### **Após Validar que Funciona:**

1. **Ajustar Parâmetros**
   - SIMILARITY_THRESHOLD: Mude para seu caso específico
   - MAX_FEATURES: Se muita rotação, aumentar
   - ALIGNMENT_METHOD: Testar ambos (ORB e ECC)

2. **Refinar Inspection Zones**
   - Dividir zonas grandes
   - Focar em componentes críticos
   - Testar com várias posições

3. **Integrar em Produção**
   - Duplicar profile para múltiplas câmeras
   - Criar perfis por tipo de placa
   - Adicionar alertas

4. **Monitorar Resultados**
   - Rastrear histórico de inspeções
   - Detectar tendências
   - Manutenção preventiva

---

## 📚 Exemplo Completo (Pronto para Copiar)

### **Configuração para Teste Rápido:**

```
Template:    "Test_v1"
Profile:     "Test_Profile"
Handler:     "Plate alignment inspection"

Environment:
SIMILARITY_THRESHOLD=0.85
MAX_FEATURES=5000
KEEP_PERCENT=0.2
ALIGNMENT_METHOD=ORB

Inspection Zones: 3 (mínimo)
- Zone_1 (esquerda)
- Zone_2 (centro)
- Zone_3 (direita)
```

### **Resultados Esperados:**

```
Teste 1: Imagem Golden (mesma do template)
Resultado: ✅ PASS 100%

Teste 2: Imagem com rotação 2°
Resultado: ✅ PASS 95%+

Teste 3: Imagem com componente faltando
Resultado: ❌ FAIL naquela zona

Teste 4: Imagem com rotação 10°
Com ORB: ⚠️ Pode falhar
Com ECC: ✅ Deve passar
```

---

## ✅ Checklist Final de Teste

- [ ] Portal acessível
- [ ] Template criado
- [ ] Inspection zones definidas
- [ ] Profile criado
- [ ] Handler "Plate alignment inspection" selecionado
- [ ] Ambiente configurado
- [ ] Teste positivo: ✅ PASS em imagem boa
- [ ] Teste negativo: ❌ FAIL em imagem com defeito
- [ ] Teste de parâmetros: Resultados mudam conforme esperado
- [ ] Módulo funcionando! 🎉

---

**Criado:** 29 de Abril de 2026
**Tempo Estimado:** 15-20 minutos
**Status:** 🟢 Pronto para Teste
