from sqlalchemy import select

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    InspectionHandlerModel,
    InspectionTargetModel,
    InspectionZoneModel,
    InspectionLogModel,
)


class InspectionTargetController(Controller):
    _model = InspectionTargetModel

    def create(
        self,
        inspection_handler: InspectionHandlerModel,
        inspection_zone: InspectionZoneModel,
    ) -> InspectionTargetModel:
        obj = InspectionTargetModel(
            inspection_handler=inspection_handler, inspection_zone=inspection_zone
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(InspectionLogModel)
            .where(InspectionLogModel.inspection_target_id == id)
            .exists()
        ).scalar()
