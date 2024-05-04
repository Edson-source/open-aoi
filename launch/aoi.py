from launch import LaunchDescription
from launch_ros.actions import Node


def aoi_launch_description():
    aoi_image_acquisition = Node(
        package="open_aoi_services",
        executable="open_aoi_image_acquisition",
    )
    aoi_product_identification = Node(
        package="open_aoi_services",
        executable="open_aoi_product_identification",
    )
    aoi_control_execution = Node(
        package="open_aoi_services",
        executable="open_aoi_control_execution",
    )
    aoi_mediator = Node(
        package="open_aoi_services",
        executable="open_aoi_mediator",
    )
    aoi_gpio = Node(
        package="open_aoi_gpio",
        executable="open_aoi_gpio",
    )
    aoi_portal = Node(
        package="open_aoi_portal",
        executable="open_aoi_portal",
    )

    return LaunchDescription(
        [
            # Independent
            aoi_image_acquisition,
            aoi_product_identification,
            aoi_control_execution,
            aoi_gpio,
            # Dependent
            aoi_mediator,
            aoi_portal,
        ]
    )


def generate_launch_description():
    return LaunchDescription([aoi_launch_description()])
