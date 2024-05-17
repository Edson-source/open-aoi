#!/bin/bash

# This script builds selected ROS 2 packages and sets up the workspace

# Source ROS 2 setup script
source /opt/ros/foxy/setup.bash

# Build selected packages
echo "Building ROS 2 packages..."
colcon build --packages-select open_aoi_interfaces
colcon build --packages-select open_aoi_gpio --symlink-install
colcon build --packages-select open_aoi_services --symlink-install
colcon build --packages-select open_aoi_portal --symlink-install
colcon build --packages-select open_aoi_core --symlink-install

# Source the workspace setup script
source install/setup.bash

echo "ROS 2 packages built and workspace setup complete."
