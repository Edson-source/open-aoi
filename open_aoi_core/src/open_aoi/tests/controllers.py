from dotenv import load_dotenv

assert load_dotenv(".env")

import unittest
import numpy as np
from PIL import Image

from open_aoi.models import engine
from open_aoi.controllers.template import TemplateController
from open_aoi.controllers.accessor import AccessorController

from sqlalchemy.orm import Session


class TemplateDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.template_controller = TemplateController(self.session)
        self.accessor_controller = AccessorController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)

    def test_create(self):
        template = self.template_controller.create("Test", None, self.accessor)
        self.template_controller.delete(template)

    def test_list_nested(self):
        self.template_controller.list_nested()


class TemplateMinioTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.template_controller = TemplateController(self.session)
        self.accessor_controller = AccessorController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)

        im = np.random.rand(100, 100, 3) * 255
        self.im = Image.fromarray(im.astype("uint8"))

        self.template = self.template_controller.create("Test", None, self.accessor)

    def test_create_blob(self):
        self.template.publish_image(self.im)
        self.template.destroy_image()

    def test_materialize_blob(self):
        self.template.publish_image(self.im)
        self.template.materialize_image()
        self.template.destroy_image()

    def tearDown(self) -> None:
        self.template_controller.delete(self.template)
