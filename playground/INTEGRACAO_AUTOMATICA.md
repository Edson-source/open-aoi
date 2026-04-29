# 🚀 Integração Automática do Plate Alignment Inspector

## ✅ O que foi feito

O módulo `plate_alignment_inspection.py` foi **integrado automaticamente** no sistema Open AOI como um módulo padrão (default module). Agora ele carrega automaticamente cada vez que você reconstrói o Docker.

---

## 📍 Localização dos Arquivos

```
open-aoi/
├── src/open_aoi_core/open_aoi_core/content/modules/
│   └── 📄 plate_alignment_inspection.py  ← MÓDULO PADRÃO
│
└── src/open_aoi_core/open_aoi_core/
    └── 📄 settings.py  ← CONFIGURAÇÃO (ATUALIZADO!)
        ├── DEFAULT_DEFECT_TYPES["plate_alignment"]
        └── DEFAULT_MODULES[.../plate_alignment_inspection.py]
```

---

## ⚙️ Como Funciona (Automático)

### **1. Quando Docker sobe:**
```
Docker startup
    ↓
open_aoi_core inicia
    ↓
Carrega settings.py
    ↓
Popula DEFAULT_DEFECT_TYPES (incluindo "plate_alignment")
    ↓
Popula DEFAULT_MODULES (incluindo plate_alignment_inspection.py)
    ↓
Sistema cria os tipos de defeito no BD
    ↓
Sistema carrega os módulos padrão
    ↓
✅ plate_alignment_inspection está pronto no portal!
```

### **2. No Portal:**
```
CONFIGURAÇÃO → Inspection Handlers
    └─ Verá automaticamente:
       ✅ Defect Type: "Plate alignment"
       ✅ Module: "Plate alignment inspection"
       └─ Status: 🟢 (pronto para usar)
```

---

## 🔄 Como Reconstruir o Docker

### **Opção A: Reconstruir Completo (Limpo)**

```bash
# 1. Para tudo
docker compose --profile full down

# 2. Remove volume (cache do build)
docker volume rm open-aoi_aoi

# 3. Reconstrói com as novas configurações
docker compose --profile full build aoi-ros2

# 4. Sobe o sistema
docker compose --profile full up -d --build
```

**Tempo:** ~5-10 minutos
**Resultado:** Tudo limpo e novo, incluindo plate_alignment pronto

### **Opção B: Reconstruir Rápido (Mantém Dados)

```bash
# 1. Para tudo
docker compose --profile full down

# 2. Reconstrói apenas a imagem
docker compose --profile full build aoi-ros2

# 3. Sobe novamente
docker compose --profile full up -d
```

**Tempo:** ~2-3 minutos
**Resultado:** Dados do banco mantidos, módulo atualizado

### **Opção C: Apenas Restart (Mais Rápido)

Se apenas quer testar se o módulo carregou:
```bash
docker compose --profile full restart aoi-ros2
```

**Tempo:** ~30 segundos
**Resultado:** Apenas restart do container

---

## ✨ O que Mudou no Código

### **Em `settings.py`:**

```python
# NOVO DEFECT TYPE adicionado:
DEFAULT_DEFECT_TYPES = {
    ...
    "plate_alignment": {                    # ← NOVO!
        "title": "Plate alignment",
        "description": "Plate alignment and component positioning issues...",
    },
}

# MÓDULO PADRÃO já existia, mas foi atualizado:
DEFAULT_MODULES = {
    ...
    f"{MODULES_PATH}/plate_alignment_inspection.py": {
        "title": "Plate alignment inspection (ORB/ECC registration, default module)",
        "description": "Automatic image registration and zone-by-zone comparison...",
        "type": "plate_alignment",  # ← Vinculado ao novo defect type
    },
}
```

### **No código de inicialização (populate_content.py):**

O sistema automaticamente:
1. ✅ Cria o DefectType "plate_alignment"
2. ✅ Carrega o arquivo `plate_alignment_inspection.py`
3. ✅ Registra como InspectionHandler no banco de dados
4. ✅ Deixa pronto para usar no portal

---

## 🎯 Novo Fluxo (Sem Upload Manual)

### **ANTES:**
```
Docker sobe
    ↓
Portal aberto
    ↓
Vai para CONFIGURAÇÃO → Modules
    ↓
Faz upload de plate_alignment_inspection.py
    ↓
(Toda vez que reconstrói, tem que fazer upload novamente!)
```

### **DEPOIS (Agora):**
```
Docker sobe
    ↓
settings.py carrega
    ↓
DEFAULT_MODULES executa populate_content()
    ↓
plate_alignment_inspection.py carregado automaticamente
    ↓
Portal aberto
    ↓
Vai para CONFIGURAÇÃO → Inspection Handlers
    ↓
✅ Módulo já está lá! Pronto para usar!
    ↓
Cria um Profile e começa a usar
    ↓
(Funciona sempre, mesmo após rebuild!)
```

---

## 📊 Verificar se Funcionou

### **1. Após reconstituir Docker:**

```bash
# Verifique os logs
docker logs aoi-ros2 | grep -i "plate_alignment"

# Deve aparecer algo como:
# "Populating default modules"
# "Creating inspection handler: Plate alignment inspection"
```

### **2. No Portal:**

```
CONFIGURAÇÃO → Inspection Handlers

Você verá:
┌─────────────────────────────────────────┐
│  Defect Types                           │
│  ✅ Plate alignment                     │
│                                         │
│  Inspection Handlers / Modules          │
│  🟢 Plate alignment inspection          │
│     (ORB/ECC registration...)           │
└─────────────────────────────────────────┘
```

### **3. Teste Rápido:**

```
INSPEÇÃO → Profiles → Create New
    ├─ Template: [sua golden image]
    ├─ Handler: "Plate alignment inspection" ← ESTÁ AQUI!
    └─ Environment: Configure parâmetros
```

---

## 🔧 Personalizações Futuras

Se quiser modificar o módulo:

### **Para atualizar o código:**
```
1. Edite: src/open_aoi_core/open_aoi_core/content/modules/plate_alignment_inspection.py
2. Reconstrói: docker compose --profile full build aoi-ros2
3. Sobe: docker compose --profile full up -d
```

### **Para mudar a descrição:**
```
1. Edite: src/open_aoi_core/open_aoi_core/settings.py
   └─ DEFAULT_MODULES[...plate_alignment_inspection.py]
2. Reconstrói e sobe
```

### **Para mudar o defect type:**
```
1. Edite: src/open_aoi_core/open_aoi_core/settings.py
   └─ DEFAULT_DEFECT_TYPES["plate_alignment"]
2. Reconstrói e sobe
```

---

## 🚨 Se Não Aparecer no Portal

### **Checklist:**

- [ ] Docker foi reconstruído após mudança no settings.py?
  ```bash
  docker compose --profile full build aoi-ros2
  ```

- [ ] Volume foi removido (se fez mudanças no populate)?
  ```bash
  docker volume rm open-aoi_aoi
  ```

- [ ] Arquivo existe no lugar certo?
  ```bash
  ls src/open_aoi_core/open_aoi_core/content/modules/plate_alignment_inspection.py
  ```

- [ ] settings.py está correto?
  ```bash
  grep -A 3 "plate_alignment" src/open_aoi_core/open_aoi_core/settings.py
  ```

- [ ] Banco de dados foi populado?
  ```bash
  docker exec -it aoi-ros2 bash
  # Dentro do container:
  python -c "from open_aoi_core.models import DefectTypeModel; ..." 
  ```

### **Solução Nuclear (reinicia tudo):**
```bash
docker compose --profile full down -v
docker volume rm open-aoi_aoi
docker compose --profile full build aoi-ros2
docker compose --profile full up -d --build
```

---

## 📋 Resumo das Mudanças

| Arquivo | Mudança | Motivo |
|---------|---------|--------|
| `settings.py` | ✅ Adicionado `"plate_alignment"` em DEFAULT_DEFECT_TYPES | Registrar tipo de defeito |
| `settings.py` | ✅ Atualizado description em DEFAULT_MODULES | Melhorar documentação |
| `plate_alignment_inspection.py` | ✅ Já está em `content/modules/` | Arquivo no lugar certo |
| Banco de dados | ✅ Será populado automaticamente | Sistema automático |
| Portal | ✅ Módulo aparece automaticamente | Sem upload necessário |

---

## 🎉 Resultado Final

**Agora você pode:**
1. ✅ Reconstruir Docker quantas vezes quiser
2. ✅ O módulo `plate_alignment_inspection` está sempre lá
3. ✅ Não precisa fazer upload manual
4. ✅ Pronto para usar imediatamente no portal
5. ✅ Pode compartilhar o código com a equipe

**Fluxo simplificado:**
```
docker compose --profile full up -d --build
    ↓
Espera 30 segundos
    ↓
Abre portal
    ↓
Vai para Inspection Handlers
    ↓
✅ Plate alignment está lá!
    ↓
Cria Profile e começa a usar
```

---

## 📚 Próximos Passos

1. **Teste agora:**
   ```bash
   docker compose --profile full down
   docker volume rm open-aoi_aoi
   docker compose --profile full build aoi-ros2
   docker compose --profile full up -d --build
   ```

2. **Abra o portal** (após 1-2 min de startup)
   ```
   http://127.0.0.1:10006
   ```

3. **Vá para CONFIGURAÇÃO → Inspection Handlers**
   - Verá o módulo "Plate alignment inspection" pronto

4. **Crie um Profile e use**
   - Sem upload manual necessário!

---

**Criado:** 29 de Abril de 2026
**Status:** ✅ Integração Completa
**Próximo:** Testar no portal
