from typing import List
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi.controllers import Controller
from open_aoi.models import (
    ControlHandlerModel,
    DefectTypeModel,
    ControlTargetModel,
)


class ControlHandlerController(Controller):
    _model = ControlHandlerModel

    def create(
        self, title: str, description: str, defect_type: DefectTypeModel
    ) -> ControlHandlerModel:
        """
        Create blank controller representation, should be
        populated with content separately (due to UI file upload util)
        """
        obj = ControlHandlerModel(
            title=title, description=description, defect_type=defect_type
        )
        self.session.add(obj)
        return obj

    def list_nested(self) -> List[ControlHandlerModel]:
        return (
            self.session.query(self._model)
            .options(joinedload(ControlHandlerModel.defect_type))
            .all()
        )

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(ControlTargetModel)
            .where(ControlTargetModel.control_handler_id == id)
            .exists()
        ).scalar()

    def post_delete_hook(self, obj: ControlHandlerModel):
        if obj.is_valid:
            obj.destroy_source()

    test_store_connection = _model.test_store_connection
