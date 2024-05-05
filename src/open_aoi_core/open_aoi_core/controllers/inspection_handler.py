from typing import List

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    InspectionHandlerModel,
    DefectTypeModel,
    InspectionTargetModel,
)


class InspectionHandlerController(Controller):
    _model = InspectionHandlerModel

    # Aliases
    test_minio_connection = InspectionHandlerModel.test_minio_connection

    def create(
        self, title: str, description: str, defect_type: DefectTypeModel
    ) -> InspectionHandlerModel:
        """
        Create blank controller representation, should be
        populated with content separately (due to UI file upload util)
        """
        entity = InspectionHandlerModel(
            title=title, description=description, defect_type=defect_type
        )
        self.session.add(entity)
        return entity

    def list_nested(self) -> List[InspectionHandlerModel]:
        """List inspection handlers with defect types"""
        return (
            self.session.query(self._model)
            .options(joinedload(InspectionHandlerModel.defect_type))
            .all()
        )

    def allow_delete_hook(self, id: int) -> bool:
        """Prevent delete is inspection target use inspection handler"""
        return not self.session.query(
            select(InspectionTargetModel)
            .where(InspectionTargetModel.inspection_handler_id == id)
            .exists()
        ).scalar()

    def post_delete_hook(self, entity: InspectionHandlerModel):
        """Delete inspection handler source"""
        if entity.has_source_blob:
            entity.destroy_source()
