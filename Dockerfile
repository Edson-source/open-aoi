FROM ros:foxy-ros-base

WORKDIR /aoi/open_aoi
COPY . /aoi/open_aoi

# Python and cv2 dependencies
RUN apt-get update && apt install software-properties-common python3-pip libgl1 -y
RUN python3 -m pip install --upgrade pip

# Colcon
RUN add-apt-repository universe
RUN apt install python3-colcon-common-extensions  -y

# Build ROS2 Open AOI packages
RUN bash aoi.build.bash
# Install python dependencies and copy default content
RUN bash aoi.install.bash

CMD ["bash", "/aoi/open_aoi/aoi.launch.bash"]
