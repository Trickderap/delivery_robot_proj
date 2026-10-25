import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MissionManagerNode(Node):
    def __init__(self):
        super().__init__('mission_manager_node')

        # Valid states defined in project spec
        self.states = [
            'IDLE',
            'TO_CANTEEN',
            'LOADING',
            'TO_DELIVERY',
            'AWAITING_PICKUP'
        ]
        self.current_state = 'IDLE'

        # Publisher: broadcasts current state to QR node and other modules
        self.state_pub = self.create_publisher(String, '/robot_state', 10)

        # Subscriber: listens for events from Web Bridge or Navigation
        self.event_sub = self.create_subscription(
            String, '/mission_event', self.event_callback, 10
        )

        # Broadcast state every 1 second so late-joining nodes stay synced
        self.timer = self.create_timer(1.0, self.publish_state)
        self.get_logger().info(f'Mission Manager initialized in state: {self.current_state}')

    def publish_state(self):
        msg = String()
        msg.data = self.current_state
        self.state_pub.publish(msg)

    def transition_to(self, new_state: str):
        if new_state in self.states:
            self.get_logger().info(f'State Transition: {self.current_state} -> {new_state}')
            self.current_state = new_state
            self.publish_state()

    def event_callback(self, msg: String):
        event = msg.data.strip().upper()
        self.get_logger().info(f'Received event: {event}')

        # State machine transition logic
        if self.current_state == 'IDLE' and event == 'START_ORDER':
            self.transition_to('TO_CANTEEN')
            # TODO: Trigger Nav2 to Canteen coordinates here

        elif self.current_state == 'TO_CANTEEN' and event == 'ARRIVED_CANTEEN':
            self.transition_to('LOADING')

        elif self.current_state == 'LOADING' and event == 'LOAD_COMPLETE':
            self.transition_to('TO_DELIVERY')
            # TODO: Trigger Nav2 to Delivery coordinates here

        elif self.current_state == 'TO_DELIVERY' and event == 'ARRIVED_DELIVERY':
            self.transition_to('AWAITING_PICKUP')

        elif self.current_state == 'AWAITING_PICKUP' and event == 'UNLOCK_COMMAND':
            self.get_logger().info('Unlock verified! Opening compartment and resetting to IDLE.')
            self.transition_to('IDLE')


def main(args=None):
    rclpy.init(args=args)
    node = MissionManagerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()