# This script install custom python dependencies to 
# ament folder structure. This script is ment to be used
# for package development. Make sure to run `colcon build` first
# to initiate required folder structure.Python packages will be available using global interpreter after running
# following commands (packages are not installed globally, only added to python path,
# see `echo $PYTHONPATH`):
# >>> source /opt/ros/foxy/setup.bash && source install/setup.bash

SITE_PACKAGES="install/open_aoi_ros_services/lib/python3.8/site-packages"
REQUIREMENTS="requirements.txt"

# Install python dependencies: ROS services
if test -d $SITE_PACKAGES; then
    echo "Install python dependencies for AOI ROS services"
    pip3 install --upgrade -r $REQUIREMENTS --target=$SITE_PACKAGES
    pip3 install pyopenssl --upgrade --target=$SITE_PACKAGES
else
    echo "Unable to install dependencies - ament workspace is not initialized. Not found: $SITE_PACKAGES"
fi
