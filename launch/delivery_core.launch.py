from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='delivery_core',
            executable='mission_manager_node',
            name='mission_manager_node',
            output='screen'
        ),
        Node(
            package='delivery_core',
            executable='qr_display_node',
            name='qr_display_node',
            output='screen'
        ),
        Node(
            package='delivery_core',
            executable='web_bridge_node',
            name='web_bridge_node',
            output='screen',
            parameters=[{'fastapi_ws_url': 'ws://localhost:8000/ws/robot'}]
        ),
    ])