FROM ros:foxy-ros-base
#python-rpi.gpio python3-rpi.gpio &&

# Install dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common python3-pip libgl1 tesseract-ocr python3-psutil && \
    python3 -m pip install --upgrade pip && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y python3-colcon-common-extensions && \
    python3 -m pip install psutil

# Set the working directory
WORKDIR /aoi/open_aoi

# Copy the application files
COPY . /aoi/open_aoi
RUN chmod +x /aoi/open_aoi/aoi.build.bash /aoi/open_aoi/aoi.install.bash /aoi/open_aoi/aoi.launch.bash

# Build ROS2 Open AOI packages
RUN /aoi/open_aoi/aoi.build.bash

# Install python dependencies and copy default content
RUN /aoi/open_aoi/aoi.install.bash

# Set the default command to launch the application
CMD ["/aoi/open_aoi/aoi.launch.bash"]
