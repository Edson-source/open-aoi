import numpy as np
from sensor_msgs.msg import Image


def encode_image(self, im: np.ndarray):
    msg = Image()
    msg.header.stamp = self.get_clock().now().to_msg()
    msg.header.frame_id = "0"
    msg.encoding = "bgr8"
    msg.height, msg.width = im.shape[:2]
    msg.step = msg.width
    msg.data = im.flatten().astype(int).tolist()
    return msg


def decode_image(msg: Image) -> np.ndarray:
    data = np.array(msg.data)
    return data.reshape((msg.height, msg.width))
