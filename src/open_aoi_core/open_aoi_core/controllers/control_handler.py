from typing import List

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    ControlHandlerModel,
    DefectTypeModel,
    ControlTargetModel,
)


class ControlHandlerController(Controller):
    _model = ControlHandlerModel

    # Aliases
    test_store_connection = ControlHandlerModel.test_store_connection

    def create(
        self, title: str, description: str, defect_type: DefectTypeModel
    ) -> ControlHandlerModel:
        """
        Create blank controller representation, should be
        populated with content separately (due to UI file upload util)
        """
        entity = ControlHandlerModel(
            title=title, description=description, defect_type=defect_type
        )
        self.session.add(entity)
        return entity

    def list_nested(self) -> List[ControlHandlerModel]:
        """List control handlers with defect types"""
        return (
            self.session.query(self._model)
            .options(joinedload(ControlHandlerModel.defect_type))
            .all()
        )

    def allow_delete_hook(self, id: int) -> bool:
        """Prevent delete is control target use control handler"""
        return not self.session.query(
            select(ControlTargetModel)
            .where(ControlTargetModel.control_handler_id == id)
            .exists()
        ).scalar()

    def post_delete_hook(self, obj: ControlHandlerModel):
        """Delete control handler source"""
        if obj.is_valid:
            obj.destroy_source()
