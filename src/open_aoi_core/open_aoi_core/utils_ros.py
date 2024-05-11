# initial code from https://github.com/ros-perception/vision_opencv/blob/noetic/cv_bridge/python/cv_bridge/core.py
import numpy as np
import sensor_msgs


def cv2_to_imgmsg(cvim, encoding="passthrough", header=None):
    if not isinstance(cvim, (np.ndarray, np.generic)):
        raise TypeError("Your input type is not a numpy array")
    # prepare msg
    img_msg = sensor_msgs.msg.Image()
    img_msg.height = cvim.shape[0]
    img_msg.width = cvim.shape[1]
    if header is not None:
        img_msg.header = header
    # encoding handling
    numpy_type_to_cvtype = {
        "uint8": "8U",
        "int8": "8S",
        "uint16": "16U",
        "int16": "16S",
        "int32": "32S",
        "float32": "32F",
        "float64": "64F",
    }
    numpy_type_to_cvtype.update(dict((v, k) for (k, v) in numpy_type_to_cvtype.items()))
    if len(cvim.shape) < 3:
        cv_type = "{}C{}".format(numpy_type_to_cvtype[cvim.dtype.name], 1)
    else:
        cv_type = "{}C{}".format(numpy_type_to_cvtype[cvim.dtype.name], cvim.shape[2])
    if encoding == "passthrough":
        img_msg.encoding = cv_type
    else:
        img_msg.encoding = encoding
    if cvim.dtype.byteorder == ">":
        img_msg.is_bigendian = True
    # img data to msg data
    img_msg.data = cvim.tostring()
    img_msg.step = len(img_msg.data) // img_msg.height

    return img_msg


def imgmsg_to_cv2(img_msg, dtype=np.uint8):
    # it should be possible to determine dtype from img_msg.encoding but there is many different cases to take into account
    # original function args: imgmsg_to_cv2(img_msg, desired_encoding = "passthrough")
    return np.frombuffer(img_msg.data, dtype=dtype).reshape(
        img_msg.height, img_msg.width, -1
    )
