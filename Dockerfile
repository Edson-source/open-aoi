FROM ros:foxy-ros-base

WORKDIR /aoi/open_aoi
COPY . /aoi/open_aoi

# General
RUN apt-get update
RUN apt install software-properties-common python3-pip -y
RUN add-apt-repository universe
RUN python3 -m pip install --upgrade pip

# Colcon
RUN apt install python3-colcon-common-extensions  -y

RUN bash aoi.build.bash
RUN bash aoi.install.bash

CMD ["bash", "aoi.launch.bash"]