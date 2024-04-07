from sqlalchemy import select

from open_aoi.controllers import Controller
from open_aoi.models import (
    ControlHandlerModel,
    ControlTargetModel,
    ControlZoneModel,
    InspectionLogModel,
)


class ControlTargetController(Controller):
    _model = ControlTargetModel

    def create(
        self,
        control_handler: ControlHandlerModel,
        control_zone: ControlZoneModel,
    ) -> ControlTargetModel:
        obj = ControlTargetModel(
            control_handler=control_handler, control_zone=control_zone
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(InspectionLogModel)
            .where(InspectionLogModel.control_target_id == id)
            .exists()
        ).scalar()
