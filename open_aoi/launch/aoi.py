from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler
from launch.events.process.process_exited import ProcessExited
from launch.event_handlers.on_process_exit import OnProcessExit


def on_exit_restart(event: ProcessExited, context):
    print(
        "[Custom handler] Process [{}] exited, pid: {}, return code: {}\n\n".format(
            event.action.name, event.pid, event.returncode
        )
    )
    if event.returncode != 0 and "aoi" in event.action.name:
        print(f"Respawning AOI service: {event.action.name}")
        return aoi_launch_description()  # Respawn node


def aoi_launch_description():
    aoi_image_acquisition = Node(
        package="open_aoi_ros_services",
        executable="aoi_image_acquisition",
    )
    aoi_identification = Node(
        package="open_aoi_ros_services",
        executable="aoi_identification",
    )
    aoi_portal = Node(
        package="open_aoi_portal",
        executable="app",
    )
    return LaunchDescription([aoi_image_acquisition, aoi_portal, aoi_identification])


def generate_launch_description():
    return LaunchDescription(
        [
            aoi_launch_description(),
            RegisterEventHandler(event_handler=OnProcessExit(on_exit=on_exit_restart)),
        ]
    )
