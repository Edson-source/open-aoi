**IN DEVELOPMENT! TARGET RELEASE DATE 06.2024**

# Welcome to Open AOI!
This is a ROS2 powered Automated Optical Inspection framework, developed as part of my master thesis at **BUT Brno** university. Project aims to provide development environment for PCB optical inspection tasks in production. Project targets **Raspberry Pi** platform yet it is possible to use any other general purpose computer (for most of functions). Project use **Docker** for deployment and **Nice GUI** for frontend, general architecture is described in `blueprint.drawio` file.

![System overview](/assets/open_aoi_overview.png)

## Related resources
- [OSF project and main paper on topic](https://osf.io/xr2gd/)
- [Related dataset, 300+ images (gray + color)](https://osf.io/hrvy8/)
- [BUT Brno master thesis publication](https://www.vut.cz/studenti/zav-prace/detail/161094)

---

# 🌟 Current Custom Features (Bench Inspection Optimized)
This repository contains a highly optimized branch of Open-AOI tailored for manual bench inspection, eliminating continuous conveyor belt dependencies (like mandatory barcodes) and focusing on localized precision.

### 🧠 Smart Hybrid Inspection (Sliding Window + OCR)
Our core module (`sliding_window_ocr.py`) handles physical soldering and placement imperfections gracefully:
*   **Localized Search (Region of Interest - ROI):** Instead of sweeping the whole board blindly, the system creates a search "neighborhood" around the original coordinate. This eliminates false positives (e.g., confusing R1 with R11) and drastically reduces processing time.
*   **Visual Validation (Template Matching):** Uses Normalized Cross-Correlation to verify physical format, color, and polarity. Skewed, missing, or inverted components trigger immediate visual rejection due to a drop in the similarity score.
*   **Optical Character Recognition (OCR):** Tesseract OCR integration with Otsu binarization pre-processing.
*   **Dynamic JSON Behavior:** The system accepts a JSON dictionary (`EXPECTED_LABELS`) via environment variables to dictate inspection logic:
    *   *Marked Components (e.g., Resistors, ICs):* If defined in the JSON, the system requires both visual validation **AND** OCR text validation.
    *   *Unmarked Components (e.g., Diodes, MLCCs):* If not in the JSON, the system dynamically switches to purely visual presence validation.

### ⚙️ Streamlined Architecture
*   **Lean Backend:** Removal of ghost ROS2 nodes (e.g., automatic barcode identifier) and legacy mathematical algorithms that generated false positives.
*   **Dynamic Image Acquisition:** OpenCV RGB capture optimized for webcams, with auto-focus and auto-exposure disabled for maximum read stability.

---

# 🗺️ Roadmap & Future Implementations (Industrial Grade)

### 🛠️ Hardware & Optics
- [ ] **Industrial Camera Setup:** Implement a high-resolution camera (5MP+) with a manually adjustable focal lens for maximum SMD reading clarity.
- [ ] **Controlled Illumination (Ring Light):** 3D print and install an LED Dome to eliminate solder glare and standardize contrast between the Golden Image and tested boards.

### 💻 Tooling & Automation (Offline Programming)
- [ ] **Pick & Place Injection Script:** Develop a Python script to parse manufacturing files (CSV/Gerber/Pick&Place) from the EDA software (e.g., Altium).
- [ ] **Auto-generation of Zones:** The script will insert coordinates (X, Y) and expected labels directly into the MySQL database, generating dozens of inspection "Boxes" instantly without manual drawing.
- [ ] **Board Variants Support:** Enable the script to understand board variants (e.g., ignoring components that are suppressed in specific PCB versions).

### 🤖 Intelligence & Stability
- [ ] **Fiducial Alignment:** Create a pre-alignment module that locates 2 or 3 fiducial markers on the board to lock global geometry (translation and rotation) before starting local searches.
- [ ] **SPC Trend Dashboard:** Plot graphs using historical visual scores stored in the database to predict Pick & Place machine calibration failures.
- [ ] **AI / Deep Learning Integration:** Evaluate YOLOv8 Nano integration for component classification with high batch color variance, replacing Template Matching in edge cases.

---

# Deployment Guide
Open AOI should be deployed to a computer with Bastler camera connected (in current version only Ethernet is supported). Connect camera, setup light and follow the following steps to deploy Open AOI!

## Docker mode
1. Follow Docker [installation guide](https://docs.docker.com/) and install Docker and Docker compose.
2. Create `.env` file in project root folder and fill in required variables. Use `host.docker.internal` for hosts (valid for dockr deployment only).
3. Run system with following command from project root folder.
```bash
docker compose --profile full up -d
```

## Native mode
Native mode runs ROS2 nodes outside docker, which may be desirable in some cases (support services still require docker). Make sure to use compatible version of ROS2. The system was originally developed with ROS2 Foxy (python 3.8) and may not be fully functional with other distributions.
1. Follow ROS2 [installation guide](https://docs.ros.org/) and install ROS2. 
2. Follow Docker [installation guide](https://docs.docker.com/) and install Docker and Docker compose.
3. Pull this repository to target machine.
```bash
git pull [https://github.com/ChrnyaevEK/open-aoi](https://github.com/ChrnyaevEK/open-aoi)
```
4. Run infrastructural Open AOI services.
```bash
docker compose --profile infra up -d
```
5. Build workspace and install python dependencies.
```bash
bash aoi.build.bash
bash aoi.install.bash 
```
6. Launch! 
```bash
bash aoi.launch.bash  # Launch AOI ROS services
```

# Custom Modules Development
Open AOI allow to upload custom code. To do so, use administrator profile and go to modules page. There you will be able to upload you code. Each module must inherit from core `IModule` class and define documentation string.
```python
from open_aoi_core.content.modules import IModule

DOCUMENTATION = "This is my module documentation."

class Module(IModule):
    def process(self, environment, test_image, template_image, inspection_zone_list):
        accept = True
        return [
            self.InspectionLog("My module log message.", accept)
            for chunk in inspection_zone_list
        ]

module = Module()
```

---

# 🇧🇷 Developer Quickstart & Notes (PT-BR)

## Passo a passo inicialização do sistema

**Instale o Docker Desktop:**
[Guia de Instalação Windows](https://docs.docker.com/desktop/setup/install/windows-install/?uuid=5A005D38-5A61-475C-8459-799CDD901479#wsl-verification-and-setup)

**1. Derruba tudo**
```bash
docker compose --profile full down
```

**2. Remove volume para limpeza do cache**
```bash
docker volume rm open-aoi_aoi
```

**3. Reconstrói com as novas configurações (sem GPIO/Barcode)**
```bash
docker compose --profile full build aoi-ros2
```

**4. Sobe o sistema em background**
```bash
docker compose --profile full up -d --build
```
*   **IP Aplicação:** `127.0.0.1:10006`
*   **Login:** `Administrator`
*   **Senha:** `senha_admin`

**5. Roda o servidor da câmera**
```bash
python .\camera_server.py
```
*   **IP Câmera:** `127.0.0.1:5000/video`

## Parâmetros de Profile Padrão (Environment)
*Utilizados na configuração dos perfis de inspeção na interface Web.*
```env
SLIDING_WINDOW_MATCH_THRESHOLD=0.85
SEARCH_MARGIN=40
EXPECTED_LABELS={"0": "103", "1": "102"}
# ALIGNMENT_METHOD=ECC (Uso futuro)
```