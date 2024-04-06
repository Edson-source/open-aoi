source /opt/ros/foxy/setup.bash

colcon build --packages-select open_aoi_ros_interfaces
colcon build --packages-select open_aoi_ros_services --symlink-install
colcon build --packages-select open_aoi_portal --symlink-install

source install/setup.bash