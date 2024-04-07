from dotenv import load_dotenv

assert load_dotenv(".env")

import unittest
import numpy as np
from PIL import Image

from open_aoi.models import engine
from open_aoi.controllers.template import TemplateController
from open_aoi.controllers.accessor import AccessorController

from sqlalchemy.orm import Session


class TemplateControllerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.template_controller = TemplateController(self.session)
        self.accessor_controller = AccessorController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)

    def test_create_delete_record(self):
        t = self.template_controller.create("Test", None, self.accessor)
        self.template_controller.delete(t)

    def test_list_nested_records(self):
        self.assertIsInstance(self.template_controller.list_nested(), list)

    def test_create_delete_blob(self):
        im = np.random.rand(100, 100, 3) * 255
        im = Image.fromarray(im.astype("uint8"))

        t = self.template_controller.create("Test", None, self.accessor)
        blob = t.publish_image(im)
        t.image_blob = blob
        self.session.commit()
        t.destroy_image()
        self.template_controller.delete(t)
