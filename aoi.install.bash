#!/bin/bash

# This script installs custom Python dependencies to 
# the ament folder structure. This script is meant to be used
# for package development. Ensure to run `colcon build` first
# to initialize the required folder structure. Python packages 
# will be available using the global interpreter after running
# the following commands (packages are not installed globally, 
# only added to the Python path, see `echo $PYTHONPATH`):
# >>> source /opt/ros/foxy/setup.bash && source install/setup.bash

# Variables
SITE_PACKAGES="install/open_aoi_core/lib/python3.8/site-packages"
REQUIREMENTS="requirements.txt"

# Function to install Python dependencies
install_dependencies() {
    echo "Installing Python dependencies for AOI ROS services"
    pip3 install -r $REQUIREMENTS --target=$SITE_PACKAGES
    pip3 install pyopenssl --upgrade --target=$SITE_PACKAGES
}

# Check if the site-packages directory exists
if [[ -d $SITE_PACKAGES ]]; then
    install_dependencies
else
    echo "Unable to install dependencies - ament workspace is not initialized. Directory not found: $SITE_PACKAGES"
    exit 1
fi

# Source ROS 2 and workspace setup scripts
source /opt/ros/foxy/setup.bash
source install/setup.bash

# Copy default content to database
# ! This will drop the current database content !
cd src/open_aoi_core/open_aoi_core/ || { echo "Directory not found: src/open_aoi_core/open_aoi_core/"; exit 1; }
python3 -m content.populate_content || { echo "Failed to populate content"; exit 1; }
cd ../../../

echo "Setup and installation complete."
