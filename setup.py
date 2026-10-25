import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'delivery_core'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='vgu_user',
    maintainer_email='vgu_user@todo.todo',
    description='ROS 2 Core, Mission Manager & Display Module for delivery robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mission_manager_node = delivery_core.mission_manager_node:main',
            'qr_display_node = delivery_core.qr_display_node:main',
            'web_bridge_node = delivery_core.web_bridge_node:main',
        ],
    },
)