FROM ros:foxy-ros-base

# Install dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common python3-pip libgl1 && \
    python3 -m pip install --upgrade pip && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y python3-colcon-common-extensions

# Set the working directory
WORKDIR /aoi/open_aoi

# Copy only the necessary scripts and files first to leverage caching
COPY aoi.build.bash aoi.install.bash aoi.launch.bash /aoi/open_aoi/
RUN chmod +x /aoi/open_aoi/aoi.build.bash /aoi/open_aoi/aoi.install.bash /aoi/open_aoi/aoi.launch.bash

# Copy the rest of the application files
COPY . /aoi/open_aoi

# Build ROS2 Open AOI packages
RUN /aoi/open_aoi/aoi.build.bash

# Install python dependencies and copy default content
RUN /aoi/open_aoi/aoi.install.bash

# Set the default command to launch the application
CMD ["bash", "/aoi/open_aoi/aoi.launch.bash"]
