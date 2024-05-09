import numpy as np
from sensor_msgs.msg import Image as Image


def image_to_msg(im: np.ndarray):
    """Convert image for to ROS image message format"""
    msg = Image()
    msg.encoding = "bgr8"
    msg.height, msg.width = im.shape[:2]
    msg.step = msg.width
    msg.data = im.flatten().astype(int).tolist()
    return msg


def msg_to_image(msg: Image) -> np.ndarray:
    """Convert image from ROS image format"""
    data = np.array(msg.data)
    return data.reshape((msg.height, msg.width, 3))
