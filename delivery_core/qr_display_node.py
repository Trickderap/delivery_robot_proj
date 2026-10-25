import time
import json
import secrets
import qrcode
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class QRDisplayNode(Node):
    def __init__(self):
        super().__init__('qr_display_node')

        # =====================================================================
        # FASTAPI QR CONFIGURATION (Easy to adjust when integrating with backend)
        # =====================================================================
        # Rotation interval in seconds (Spec: 30-60s)
        self.declare_parameter('rotation_interval', 30.0)
        # Template for QR content.
        # Use "{token}" for raw token, or "http://<FASTAPI_IP>:8000/unlock?token={token}"
        self.declare_parameter('qr_payload_template', '{token}')

        self.rotation_interval = self.get_parameter('rotation_interval').value
        self.qr_template = self.get_parameter('qr_payload_template').value
        # =====================================================================

        self.robot_state = 'IDLE'
        self.last_rotation_time = 0.0
        self.window_open = False

        # Subscribe to robot state from Mission Manager
        self.state_sub = self.create_subscription(
            String, '/robot_state', self.state_callback, 10
        )

        # Publisher: sends active QR token data to Web Bridge -> FastAPI
        self.token_pub = self.create_publisher(String, '/qr_token', 10)

        # UI refresh loop (10 Hz)
        self.ui_timer = self.create_timer(0.1, self.ui_loop)
        self.get_logger().info('QR Display Node ready (Two-Way Sync enabled).')

    def state_callback(self, msg: String):
        self.robot_state = msg.data

    def generate_and_show_qr(self):
        now = int(time.time())
        expires_at = now + int(self.rotation_interval)
        raw_token = secrets.token_hex(4).upper()  # e.g., "A1B2C3D4"

        # 1. Publish token metadata to ROS 2 so Web Bridge can sync with FastAPI
        token_msg = String()
        token_msg.data = json.dumps({
            "token": raw_token,
            "expires_at": expires_at
        })
        self.token_pub.publish(token_msg)

        # 2. Format what the phone camera actually scans inside the QR image
        qr_content = self.qr_template.format(token=raw_token, exp=expires_at)
        self.get_logger().info(f'Rotated QR Token: {raw_token} (Valid for {int(self.rotation_interval)}s)')

        # 3. Render QR image using Python qrcode library
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_content)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        cv_img = np.array(pil_img)
        cv2.imshow("Robot Display - Scan to Unlock", cv_img)
        self.window_open = True

    def ui_loop(self):
        if self.robot_state == 'AWAITING_PICKUP':
            now = time.time()
            if (now - self.last_rotation_time) >= self.rotation_interval:
                self.generate_and_show_qr()
                self.last_rotation_time = now
            cv2.waitKey(1)
        else:
            if self.window_open:
                cv2.destroyAllWindows()
                self.window_open = False
                self.last_rotation_time = 0.0


def main(args=None):
    rclpy.init(args=args)
    node = QRDisplayNode()
    rclpy.spin(node)
    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()