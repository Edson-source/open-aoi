from datetime import datetime

from open_aoi.controllers import Controller
from open_aoi.models import (
    InspectionModel,
    InspectionLogModel,
    ControlTargetModel,
)


class ControlLogController(Controller):
    _model = InspectionLogModel

    def create(
        self,
        control_target: ControlTargetModel,
        inspection: InspectionModel,
        log: str,
        passed: bool,
    ) -> InspectionLogModel:
        obj = InspectionLogModel(
            control_target=control_target,
            inspection=inspection,
            log=log,
            passed=passed,
            created_at=datetime.now(),
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return False  # Do not delete log
