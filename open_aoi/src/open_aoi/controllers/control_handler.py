from open_aoi.controllers import Controller
from open_aoi.models import ControlHandlerModel


class ControlHandlerController(Controller):
    _model = ControlHandlerModel

    @classmethod
    def create(cls):
        raise NotImplemented()

    validate_source = _model.validate_source
