# Delivery Robot - ROS 2 Core Module

This package contains the central Mission Manager (FSM), the Dynamic QR Code Display for the robot's physical screen, and the Web Bridge that connects the ROS 2 ecosystem to the FastAPI backend.

## 1. Dependencies

This package requires **ROS 2 Humble** (Ubuntu 22.04) and the following Python libraries:
```bash
pip3 install "qrcode[pil]" opencv-python websockets
```
*(Note for Raspberry Pi: Install OpenCV via `sudo apt install python3-opencv` instead of pip to save build time and avoid Qt font errors).*

## 2. Building the Package

Clone this repository into the `src` folder of your ROS 2 workspace, then build it:
```bash
cd ~/delivery_robot_ws/src
git clone <YOUR_GITHUB_REPO_URL> delivery_core
cd ~/delivery_robot_ws
colcon build --packages-select delivery_core
source install/setup.bash
```

## 3. Running the System

Start all three nodes (Mission Manager, QR Display, and Web Bridge) simultaneously using the launch file:
```bash
export DISPLAY=:0  # Required on Raspberry Pi for the QR window to render physically
ros2 launch delivery_core delivery_core.launch.py
```

### Changing the FastAPI WebSocket URL
By default, the Web Bridge connects to `ws://localhost:8000/ws/robot`. To point the robot to the production cloud server or a teammate's laptop, override the parameter at launch:
```bash
ros2 launch delivery_core delivery_core.launch.py fastapi_ws_url:="wss://your-cloud-server.com/ws/robot"
```

## 4. System Architecture

* **`mission_manager_node`**: Manages states (`IDLE` -> `TO_CANTEEN` -> `LOADING` -> `TO_DELIVERY` -> `AWAITING_PICKUP`). Listens to `/mission_event` and broadcasts `/robot_state`.
* **`qr_display_node`**: Pops up a local OpenCV window when the robot enters `AWAITING_PICKUP`. Generates a time-restricted token that rotates every 30 seconds and publishes it to `/qr_token`.
* **`web_bridge_node`**: Maintains an async WebSocket connection to FastAPI. Forwards backend commands (`UNLOCK`, `START_ORDER`) to `/mission_event` and syncs `/robot_state` back to the server.