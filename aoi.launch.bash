echo Welcome to Open AOI!
source /opt/ros/foxy/setup.bash    # Source ROS2
source install/setup.bash          # Source Open-AOI stack

cp .env ./src/open_aoi_core/open_aoi_core
ros2 launch launch/aoi.py          # Launch AOI services and bridge
