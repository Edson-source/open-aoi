import os

MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
assert MYSQL_DATABASE

MYSQL_USER = os.environ["MYSQL_USER"]
assert MYSQL_USER

MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
assert MYSQL_PASSWORD

MYSQL_PORT = os.environ["MYSQL_PORT"]
assert MYSQL_PORT
try:
    MYSQL_PORT = int(MYSQL_PORT)
except ValueError:
    raise RuntimeError("Failed to parse mysql port from environment")

ROS_PORT = os.environ["ROS_PORT"]
assert ROS_PORT
try:
    ROS_PORT = int(ROS_PORT)
except ValueError:
    raise RuntimeError("Failed to parse ROS port from environment")

WEB_INTERFACE_PORT = os.environ["WEB_INTERFACE_PORT"]
assert WEB_INTERFACE_PORT
try:
    WEB_INTERFACE_PORT = int(WEB_INTERFACE_PORT)
except ValueError:
    raise RuntimeError("Failed to parse web port from environment")

ALLOW_SIMULATION_NODE = os.environ["SIMULATION"] == "1"

AOI_OPERATOR_INITIAL_PASSWORD = os.environ["AOI_OPERATOR_INITIAL_PASSWORD"]
assert AOI_OPERATOR_INITIAL_PASSWORD

AOI_ADMINISTRATOR_INITIAL_PASSWORD = os.environ["AOI_ADMINISTRATOR_INITIAL_PASSWORD"]
assert AOI_ADMINISTRATOR_INITIAL_PASSWORD

STORAGE_SECRET = os.environ["STORAGE_SECRET"]
assert STORAGE_SECRET and len(STORAGE_SECRET) > 10

MINIO_PORT = os.environ["MINIO_PORT"]
assert MINIO_PORT

MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
assert MINIO_ACCESS_KEY

MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
assert MINIO_SECRET_KEY
