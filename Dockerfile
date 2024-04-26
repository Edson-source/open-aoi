FROM ros:foxy-ros-base

WORKDIR /aoi/open_aoi
COPY open_aoi /aoi/open_aoi

# General
RUN apt-get update
RUN apt install software-properties-common python3-pip -y
RUN add-apt-repository universe
RUN python3 -m pip install --upgrade pip

# Colcon
RUN apt install python3-colcon-common-extensions  -y

# Ros2 bridge for external communication (web interface)
RUN apt install ros-foxy-rosbridge-*  -y
RUN bash aoi.build.bash
RUN bash aoi.setup.bash

CMD ["bash", "aoi.launch.bash"]