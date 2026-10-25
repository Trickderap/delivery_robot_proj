import asyncio
import threading
import queue
import json
import websockets
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class WebBridgeNode(Node):
    def __init__(self):
        super().__init__('web_bridge_node')

        # =====================================================================
        # FASTAPI CONNECTION PARAMETERS (Override via CLI or Launch file)
        # =====================================================================
        self.declare_parameter('fastapi_ws_url', 'ws://localhost:8000/ws/robot')
        self.declare_parameter('robot_id', 'robot_01')

        self.ws_url = self.get_parameter('fastapi_ws_url').value
        self.robot_id = self.get_parameter('robot_id').value
        # =====================================================================

        self.last_sent_state = None
        self.outbound_queue = queue.Queue()

        # Publisher: feeds FastAPI commands into ROS 2 Mission Manager
        self.event_pub = self.create_publisher(String, '/mission_event', 10)

        # Subscribers: listen to ROS 2 state and QR tokens to send to FastAPI
        self.state_sub = self.create_subscription(
            String, '/robot_state', self.state_callback, 10
        )
        self.token_sub = self.create_subscription(
            String, '/qr_token', self.token_callback, 10
        )

        # Start background asyncio thread for WebSocket communication
        self.ws_thread = threading.Thread(target=self.start_async_loop, daemon=True)
        self.ws_thread.start()
        self.get_logger().info(f'Web Bridge ready. Target FastAPI URL: {self.ws_url}')

    # =========================================================================
    # FASTAPI ADAPTER SECTION (Edit JSON keys here to match team's API)
    # =========================================================================
    def format_state_for_fastapi(self, state: str) -> str:
        """ Outbound JSON when robot changes state (IDLE, TO_CANTEEN, etc.) """
        return json.dumps({
            "type": "state_update",
            "robot_id": self.robot_id,
            "state": state
        })

    def format_token_for_fastapi(self, token_data: dict) -> str:
        """ Outbound JSON when a new 30-60s QR token is generated """
        return json.dumps({
            "type": "qr_token_update",
            "robot_id": self.robot_id,
            "token": token_data.get("token"),
            "expires_at": token_data.get("expires_at")
        })

    def parse_command_from_fastapi(self, raw_msg: str) -> str:
        """ Inbound JSON parser: extracts command sent from FastAPI """
        try:
            data = json.loads(raw_msg)
            # Supports {"command": "UNLOCK"}, {"action": "UNLOCK"}, or {"event": "UNLOCK"}
            cmd = data.get('command') or data.get('action') or data.get('event') or ''
            return cmd.strip().upper()
        except json.JSONDecodeError:
            return raw_msg.strip().upper()
    # =========================================================================

    def state_callback(self, msg: String):
        # Only push to FastAPI when the state actually changes (or on first connect)
        if msg.data != self.last_sent_state:
            self.last_sent_state = msg.data
            payload = self.format_state_for_fastapi(msg.data)
            self.outbound_queue.put(payload)

    def token_callback(self, msg: String):
        try:
            token_data = json.loads(msg.data)
            payload = self.format_token_for_fastapi(token_data)
            self.outbound_queue.put(payload)
        except json.JSONDecodeError:
            pass

    def start_async_loop(self):
        asyncio.run(self.websocket_handler())

    async def websocket_handler(self):
        while rclpy.ok():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.get_logger().info('Connected to FastAPI WebSocket server!')
                    # Force re-send current state upon connection
                    if self.last_sent_state:
                        await websocket.send(self.format_state_for_fastapi(self.last_sent_state))

                    # Run inbound listener and outbound sender concurrently
                    receive_task = asyncio.create_task(self.receive_loop(websocket))
                    send_task = asyncio.create_task(self.send_loop(websocket))
                    done, pending = await asyncio.wait(
                        [receive_task, send_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
            except Exception as e:
                self.get_logger().warn(f'WebSocket disconnected ({e}). Retrying in 3s...')
                await asyncio.sleep(3.0)

    async def receive_loop(self, websocket):
        async for message in websocket:
            command = self.parse_command_from_fastapi(message)
            valid_cmds = {
                'UNLOCK': 'UNLOCK_COMMAND',
                'UNLOCK_COMMAND': 'UNLOCK_COMMAND',
                'START_ORDER': 'START_ORDER',
                'ARRIVED_CANTEEN': 'ARRIVED_CANTEEN',
                'LOAD_COMPLETE': 'LOAD_COMPLETE',
                'ARRIVED_DELIVERY': 'ARRIVED_DELIVERY'
            }
            if command in valid_cmds:
                ros_msg = String()
                ros_msg.data = valid_cmds[command]
                self.event_pub.publish(ros_msg)
                self.get_logger().info(f'FastAPI -> ROS 2: {ros_msg.data}')

    async def send_loop(self, websocket):
        while rclpy.ok():
            try:
                payload = self.outbound_queue.get_nowait()
                await websocket.send(payload)
                self.get_logger().info(f'ROS 2 -> FastAPI: {payload}')
            except queue.Empty:
                await asyncio.sleep(0.1)


def main(args=None):
    rclpy.init(args=args)
    node = WebBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()