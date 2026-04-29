# 🎯 Onde Fazer Upload - Guia Visual

## O Problema: Múltiplos Espaços para Upload

```
Portal tem várias seções:

✅ CONFIGURAÇÃO → Inspection Handlers
   ├─ Defect Types (tipos de defeito)
   ├─ Inspection Handlers (módulos)
   │  └─ Dentro de cada handler: [Upload source]  ← VOCÊ ESTÁ AQUI!
   └─ Outras coisas...

❌ CONFIGURAÇÃO → Câmeras
   └─ Câmeras (não upload aqui)

❌ CONFIGURAÇÃO → Templates
   └─ Imagens golden (não upload aqui)

❌ INSPEÇÃO → Profiles
   └─ Profiles (não upload aqui)
```

---

## ✅ Caminho Correto (PASSO A PASSO)

### **PASSO 1: Abra a seção de Handlers**
```
Menu Portal
    ↓
CONFIGURAÇÃO
    ↓
Inspection Handlers  ← CLIQUE AQUI
```

### **PASSO 2: Crie um Defect Type (primeira vez)**
```
Na página Inspection Handlers, lado ESQUERDO:

┌─────────────────────────────────────────┐
│  INSPECTION HANDLERS                    │
├─────────────────────────────────────────┤
│                                         │
│  ## Defect Types                        │
│  (lista de tipos de defeito)            │
│                                         │
│  [+ Create Defect Type]  ← CLIQUE AQUI  │
│                                         │
│  ---------                              │
│                                         │
│  ## Inspection Handlers / Modules       │
│  (lista de módulos/handlers)            │
│                                         │
│  [+ Create New Module]                  │
│                                         │
└─────────────────────────────────────────┘
```

**Preencha:**
- **Título:** "Placa Alignment Check"
- **Descrição:** "Verifica alinhamento e defeitos"
- Clique **Save**

### **PASSO 3: Crie um Inspection Handler**
```
Na mesma página, clique em [+ Create New Module]

Preencha:
- Título: "Plate Alignment Inspection"
- Defect Type: "Placa Alignment Check" (do passo 2)
- Clique Save
```

### **PASSO 4: Faça o Upload do Arquivo**
```
Agora você verá na lista:

┌─────────────────────────────────────────┐
│  Inspection Handlers                    │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 🟡 Plate Alignment Inspection   │   │
│  │    (Sem source file)            │   │
│  │                                 │   │
│  │  [Edit]  [Download]  [Delete]   │   │ ← CLIQUE EM EDIT!
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘

OU simplesmente clique no nome do módulo.
```

### **PASSO 5: Dentro do Editor do Handler**
```
Página que abre:

┌──────────────────────────────────────────┐
│  Edit Inspection Handler                 │
│                                          │
│  Título: Plate Alignment Inspection      │
│  Defect Type: Placa Alignment Check      │
│                                          │
│  #### Upload source                      │
│  [UPLOAD BUTTON] ← CLIQUE AQUI!          │
│                                          │
│  Selecione o arquivo:                    │
│  📄 plate_alignment_inspection.py        │
│                                          │
│  Status: ✅ Uploaded                     │
│                                          │
└──────────────────────────────────────────┘
```

---

## 🚨 Sinais de Que Funcionou

```
Antes do upload:
┌─────────────────────────────┐
│ 🟡 Plate Alignment...       │  ← Círculo AMARELO = sem source
└─────────────────────────────┘

Depois do upload:
┌─────────────────────────────┐
│ 🟢 Plate Alignment...       │  ← Círculo VERDE = source OK!
└─────────────────────────────┘

E você verá no portal:
```
✓ Uploaded plate_alignment_inspection.py
```
```

---

## ❌ Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| "Módulo não aparece na lista" | Não criou o handler | Siga PASSO 3 |
| "Não consigo fazer upload" | Upload não está ativo | Verifique PASSO 4-5 |
| "Arquivo rejeitado" | Arquivo inválido | Verifique sintaxe Python |
| "Defect Type não aparece" | Não criou tipo | Siga PASSO 2 |

---

## 📸 Resumo Visual

```
FLUXO CORRETO:

1. Portal → CONFIGURAÇÃO → Inspection Handlers
                               │
                               ├─► Create Defect Type
                               │   └─ "Placa Alignment Check"
                               │
                               └─► Create New Module
                                   └─ "Plate Alignment Inspection"
                                      │
                                      └─► Edit
                                          └─► Upload source
                                              └─ plate_alignment_inspection.py
                                                 ✅ PRONTO!
```

---

## 🎯 A Resposta Curta

**Pergunta:** Qual espaço eu uso para upload?

**Resposta:** 
```
Portal → CONFIGURAÇÃO → Inspection Handlers
                           └─ Create New Module (primeiro)
                              └─ Edit [seu módulo] (depois)
                                 └─ Upload source (aqui!)
```

**Não é em:**
- ❌ CONFIGURAÇÃO → Câmeras
- ❌ CONFIGURAÇÃO → Templates
- ❌ INSPEÇÃO → Profiles
- ❌ Qualquer outro lugar

**É em:**
- ✅ CONFIGURAÇÃO → Inspection Handlers → [seu módulo] → Upload source

---

**Criado:** 29 de Abril de 2026
