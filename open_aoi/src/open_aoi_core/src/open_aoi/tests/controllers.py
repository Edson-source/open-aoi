from dotenv import load_dotenv

assert load_dotenv(".env")

import unittest
import numpy as np
from PIL import Image

from open_aoi.models import engine
from open_aoi.controllers.template import TemplateController
from open_aoi.controllers.accessor import AccessorController
from open_aoi.controllers.control_handler import ControlHandlerController
from open_aoi.controllers.defect_type import DefectTypeController
from open_aoi.controllers.control_zone import ControlZoneController
from open_aoi.controllers.connected_component import ConnectedComponentController
from open_aoi.controllers.control_target import ControlTargetController

from sqlalchemy.orm import Session


class TemplateDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.template_controller = TemplateController(self.session)
        self.accessor_controller = AccessorController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)

    def test_create_delete(self):
        template = self.template_controller.create("Test", self.accessor, None)
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

    def test_create_destroy(self):
        self.template.publish_image(self.im)
        self.template.destroy_image()

    def test_materialize(self):
        self.template.publish_image(self.im)
        self.template.materialize_image()
        self.template.destroy_image()


class ControlHandlerDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.control_handler_controller = ControlHandlerController(self.session)
        self.accessor_controller = AccessorController(self.session)
        self.defect_type_controller = DefectTypeController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)
        self.defect_type = self.defect_type_controller.retrieve(1)

    def test_create_delete(self):
        control_handler = self.control_handler_controller.create(
            "Test", "test", self.defect_type
        )
        self.control_handler_controller.delete(control_handler)

    def test_list_nested(self):
        self.control_handler_controller.list_nested()


class ControlHandlerMinioTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.control_handler_controller = ControlHandlerController(self.session)
        self.accessor_controller = AccessorController(self.session)
        self.defect_type_controller = DefectTypeController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)
        self.defect_type = self.defect_type_controller.retrieve(1)

        self.source = """
parameters = []
process = lambda: print('hello open-aoi!')
""".encode()

        self.control_handler = self.control_handler_controller.create(
            "Test", "test", self.defect_type
        )

    def test_validate(self):
        self.assertTrue(self.control_handler.validate_source(self.source))

    def test_create_destroy(self):
        self.control_handler.publish_source(self.source)
        self.control_handler.destroy_source()

    def test_materialize(self):
        self.control_handler.publish_source(self.source)
        self.control_handler.materialize_source()
        self.control_handler.destroy_source()


class ControlZoneDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.accessor_controller = AccessorController(self.session)
        self.template_controller = TemplateController(self.session)
        self.control_zone_controller = ControlZoneController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)
        self.template = self.template_controller.create("Test", self.accessor)

    def test_create_delete(self):
        control_zone = self.control_zone_controller.create(
            "Test", self.template, self.accessor
        )
        self.control_zone_controller.delete(control_zone)

    def test_list_nested(self):
        self.control_zone_controller.list_nested()


class ConnectedComponentDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.accessor_controller = AccessorController(self.session)
        self.template_controller = TemplateController(self.session)
        self.control_zone_controller = ControlZoneController(self.session)
        self.connected_component_controller = ConnectedComponentController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)
        self.template = self.template_controller.create("Test", self.accessor)
        self.control_zone = self.control_zone_controller.create(
            self.template, self.accessor
        )

    def test_create_delete(self):
        cc = self.connected_component_controller.create(0, 0, 0, 0, self.control_zone)
        self.connected_component_controller.delete(cc)


class ControlTargetDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Session(engine)
        self.accessor_controller = AccessorController(self.session)
        self.template_controller = TemplateController(self.session)
        self.control_zone_controller = ControlZoneController(self.session)
        self.control_target_controller = ControlTargetController(self.session)
        self.control_handler_controller = ControlHandlerController(self.session)
        self.defect_type_controller = DefectTypeController(self.session)

        self.accessor = self.accessor_controller.retrieve(1)
        self.defect_type = self.defect_type_controller.retrieve(1)
        self.template = self.template_controller.create("Test", self.accessor)
        self.control_zone = self.control_zone_controller.create(
            self.template, self.accessor
        )
        self.control_handler = self.control_handler_controller.create(
            "Test", "test", self.defect_type
        )

    def test_create_delete(self):
        control_target = self.control_target_controller.create(
            self.control_handler, self.control_zone
        )
        self.control_target_controller.delete(control_target)
