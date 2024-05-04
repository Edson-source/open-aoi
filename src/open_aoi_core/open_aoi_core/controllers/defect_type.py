from sqlalchemy import select

from open_aoi_core.controllers import Controller
from open_aoi_core.models import DefectTypeModel, InspectionHandlerModel


class DefectTypeController(Controller):
    _model = DefectTypeModel

    def create(self, title: str, description: str):
        """Create defect type entity"""
        entity = DefectTypeModel(
            title=title,
            description=description,
        )
        self.session.add(entity)
        return entity

    def allow_delete_hook(self, id: int) -> bool:
        """Allow delete if no inspection handler use this defect type"""
        return not self.session.query(
            select(InspectionHandlerModel)
            .where(InspectionHandlerModel.defect_type_id == id)
            .exists()
        ).scalar()
