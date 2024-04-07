from sqlalchemy import select

from open_aoi.controllers import Controller
from open_aoi.models import DefectTypeModel, ControlHandlerModel


class DefectTypeController(Controller):
    _model = DefectTypeModel

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(ControlHandlerModel)
            .where(ControlHandlerModel.defect_type_id == id)
            .exists()
        ).scalar()

    def create(self, title: str, description: str):
        obj = DefectTypeModel(
            title=title,
            description=description,
        )
        self.session.add(obj)
        return obj
