source /opt/ros/foxy/setup.bash

# rosdep update --include-eol-distros
# rosdep install --from-paths src -y --ignore-src

colcon build --packages-select open_aoi_ros_interfaces
colcon build --packages-select open_aoi_ros_services --symlink-install

source install/setup.bash