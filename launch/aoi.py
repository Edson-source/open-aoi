"""
    This is main launch file for ROS framework. Script launches Open AOI services.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def aoi_launch_description():
    # Services - image acquisition
    aoi_image_acquisition = Node(
        package="open_aoi_services",
        executable="open_aoi_image_acquisition",
    )
    # Services - inspection execution node
    aoi_inspection_execution = Node(
        package="open_aoi_services",
        executable="open_aoi_inspection_execution",
    )
    # Services - mediator
    aoi_mediator = Node(
        package="open_aoi_services",
        executable="open_aoi_mediator",
    )
    # GPIO
    aoi_gpio = Node(
        package="open_aoi_gpio",
        executable="open_aoi_gpio",
    )
    # Web portal
    aoi_portal = Node(
        package="open_aoi_portal",
        executable="open_aoi_portal",
    )

    return LaunchDescription(
        [
            # Independent
            aoi_image_acquisition,
            aoi_inspection_execution,
            aoi_gpio,
            # Dependent
            # Depend on ^
            aoi_mediator,
            # Depend on ^
            aoi_portal,
        ]
    )


def generate_launch_description():
    return LaunchDescription([aoi_launch_description()])
