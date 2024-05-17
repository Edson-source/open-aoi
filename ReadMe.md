**IN DEVELOPMENT! TARGET RELEASE DATE 06.2024**

# Welcome to Open AOI!
This is a ROS2 powered Automated Optical Inspection framework, developed as part of my master thesis at **BUT Brno** university. Project aims to provide development environment for PCB optical inspection tasks in production. Project targets **Raspberry Pi** platform yet it is possible to use any other general purpose computer (for most of functions). Project use **Docker** for deployment and **Nice GUI** for frontend, general architecture is described in `blueprint.drawio` file.

![System overview](/assets/open_aoi_overview.png)

## Related resources
- [OSF project and main paper on topic](https://osf.io/xr2gd/)
- [Related dataset, 300+ images (gray + color)](https://osf.io/hrvy8/)
- [BUT Brno master thesis publication](https://www.vut.cz/studenti/zav-prace/detail/161094)

# Deployment  guide
Open AOI should be deployed to a computer with Bastler camera connected (in current version only Ethernet is supported). Connect camera, setup light and follow the following steps to deploy Open AOI!
## Docker mode
1. Follow Docker [installation guide](https://docs.docker.com/) and install Docker and Docker compose.
2. Create `.env` file in project root folder and fill in required variables. Use `host.docker.internal` for hosts (valid for dockr deployment only).
3. Run system with following command from project root folder.
```
docker compose --profile full up -d
```

## Native mode
Native mode runs ROS2 nodes outside docker, which may be desirable in some cases (support services still require docker). Make sure to use compatible version of ROS2. The system was originally developed with ROS2 Foxy (python 3.8) and may not be fully functional with other distributions.
1. Follow ROS2 [installation guide](https://docs.ros.org/) and install ROS2. 
2. Follow Docker [installation guide](https://docs.docker.com/) and install Docker and Docker compose.
3. Pull this repository to target machine.
```
git pull https://github.com/ChrnyaevEK/open-aoi
```
4. Run infrastructural Open AOI services (all except for main ROS2, which is considered main element of the system).
```
docker compose --profile infra up -d
```
5. Make sure `python3` **is python global system interpreter** and `pip3` **is available**. Check python version and update `aoi.install.bash` with your python version (default is python3.8). Run next commands to build colcon workspace and install python dependencies. Python dependencies will be installed to colcon `./install` folder and will not interfere  with global packages (will be available only after workspace is sourced, same fashion as `rclpy` package from ROS2). 
```
# Alternatively use `. aoi.<stage>.bash` to source ROS2 into current terminal

# - Build workspace (symlinks)
bash aoi.build.bash

# - Install python dependencies and upload default content
# Will create default database content and upload default modules to Minio
bash aoi.install.bash 
```
5. Launch! 
```
bash aoi.launch.bash  #  Launch AOI ROS services
```

# Architecture
The Open AOI architecture is described in details in related paper. In short, Open AOI is a collection of ROS2 nodes, that realize image acquisition, product identification from image (by barcode) and conduct inspection of the product using golden image (template). Open AOi provide editor to define basic inspection zones (rectangle on the image, tested and template, where the defect is expected), which are passed to inspection handlers (python code, which should tell good from bad) and then results are stored. The system use two types of storage - traditional relational SQL database for structured data and open source Minio blob storage to store captured images.

That is how it looks like.
![System architecture](/assets/open_aoi_architecture.png)

There are a few reasons, I chose ROS2 as basement for this system. ROS2 is well known among robotic developer and thus Open AOI may be fused with some existing project seamlessly. ROS2 also support distribution of nodes natively, which means should you need to drop executor node to another compute, with ROS2 it should be fairly simple.

Open AOI is build to communicate to the outer world by GPIO. The system allow to define single trigger pin per camera as well as single accept and reject pins. Trigger pin should be up for half a second to trigger an inspection and result will be propagated to either accept or reject pins.

![GPIO protocol](/assets/open_aoi_gpio.png)

Inspection process follows quite trivial logic. When triggered manually the camera is identified by id in trigger details. When triggered by GPIO, camera will be looked up by pin id/number. Image from related camera is then captured and product is identified (barcode). After barcode value was decoded an inspection profile and related template is pulled up. Template contains inspection zones with assigned inspection handlers. Mediator node will send each inspection handler to execution with related inspection zones. After that results are back populated. Errors are generally returned as error code and description in ROS service response once occur.

Open AOI also allow to use custom code for image inspection. During the inspection process python code (module) will be invoked and  provided with test image, templte image and inspection zones. Returned results will be logged. More on that in development section.

## Profiling
The system was profiled with 1200x1200 px sample image and simple inspection handler and the results are the following.

![Open AOI profile](/assets/open_aoi_profile.png)


# Development guide

## Custom modules development
As it was mentioned, Open AOI allow to upload custom code. To do so, use administrator profile and go to modules page. There you will be able to upload you code. 

Each module is simple python file, which is dynamically interpreted when inspection is conducted. Each module must inherit from core `IModule` class and define documentation string. If module required parameters, it should describe parameters in documentation string and expect them in `environment` variable (provided as parsed dictionary parametr).

The simplest module will look like this (file `my_fancy_module.py`): 
```
from open_aoi_core.content.modules import IModule
# Import any installed library, like opencv, numpy, etc...
# Do not import other open_aoi packages and do not call Open AOI services (may break the system)

# Required
DOCUMENTATION = "This is my module. No environment variable (parameters are used). Module does nothing."


class Module(IModule):
    def process(
        self,
        environment,  # Dictionary with key-value pairs defined in inspection profile (describe in documentation what you need to be there)
        test_image,  # Full size raw test image
        template_image,  # Full size raw template image
        inspection_zone_list  # List of inspection zone coordinates (length of returned log list MUST match length of inspection zone list)
    ):
        accept = True
        reject = False
        return [
            self.InspectionLog("My module thinks that this inspection zone is OK... or it is not.", accept)
            for chunk in inspection_zone_list
        ]

# Required
module = Module()
```

Use `playground/inspection_development/modules_production/_template.py` as template for your modules. Playground contains development environment for you algorithms and modules. Feel free to break it :-)

## Open AOI development
Basic system configuration is provided by `.env` file from root directory. This file will be copied to core ROS package upon launch and so defined variables will be available at for import from `open_aoi_core.settings` (should you add new variables, update settings file to reflect changes).
```
MYSQL_DATABASE=<SQL database>
MYSQL_USER=<SQL user name>
MYSQL_PASSWORD=<SQL user password>
MYSQL_ROOT_PASSWORD=<SQL root user password>
MYSQL_HOST=<SQL server host, 127.0.0.1>
MYSQL_PORT=<SQL server port, 10002>

AOI_OPERATOR_INITIAL_PASSWORD=<Password for operator>
AOI_ADMINISTRATOR_INITIAL_PASSWORD=<Password for administrator>

STORAGE_SECRET=<Storage secret (NiceGUI)>

MINIO_ROOT_USER=<Minio root user name>
MINIO_ROOT_PASSWORD=<Minio root user password>
MINIO_HOST=<Minio server host, 127.0.0.1>
MINIO_PORT=<Minio server port, 10004>

SIMULATION=<1|0, if 1 emulator camera will be used with GPIO emulation>
```
Once ready, follow native installation guide to install ROS2 and docker. The following development process is simple - make changes to code, run `. aoi.launch.bash`, feel frustration and repeat. Open AOI nodes communicate with each other and this is the main issue, as calling callbacks from callback is not what ROS2 was built for. However this issue was eventually solved. Try to keep services well documented and isolated. Good luck!

# Other
As bonus, there are publicly available dataset with over 300 image, taken on industrial camera. The dataset is located in OSF project files (see links on top of the page) and described in main project paper. Dataset is not labeled for any defects. Information about exposure, objective and camera, aperture and illumination conditions is however available.

![Dataset sample image](/assets/drawcore.bmp)
