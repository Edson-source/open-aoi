"""Script create DB tables"""

from dotenv import load_dotenv

assert load_dotenv(".env")

from open_aoi.models import *

if __name__ == "__main__":
    metadata_obj.drop_all(engine)
    metadata_obj.create_all(engine)
