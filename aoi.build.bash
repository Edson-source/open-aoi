#!/bin/bash

# This script builds selected ROS 2 packages and sets up the workspace

# Source ROS 2 setup script
source /opt/ros/foxy/setup.bash

# Function to build ROS 2 packages
build_packages() {
    if [ "$1" = "open_aoi_interfaces" ]; then
        colcon build --packages-select $1
    else
        colcon build --packages-select $1 --symlink-install
    fi
}

# Build selected packages
echo "Building ROS 2 packages..."
build_packages "open_aoi_interfaces"
build_packages "open_aoi_gpio"
build_packages "open_aoi_services"
build_packages "open_aoi_portal"
build_packages "open_aoi_core"

# Source the workspace setup script
source install/setup.bash

echo "ROS 2 packages built and workspace setup complete."
