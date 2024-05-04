from datetime import datetime

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    InspectionModel,
    InspectionLogModel,
    InspectionTargetModel,
)


class InspectionLogController(Controller):
    _model = InspectionLogModel

    def create(
        self,
        inspection_target: InspectionTargetModel,
        inspection: InspectionModel,
        log: str,
        passed: bool,
    ) -> InspectionLogModel:
        """Create inspection log record"""
        entity = InspectionLogModel(
            inspection_target=inspection_target,
            inspection=inspection,
            log=log,
            passed=passed,
        )
        self.session.add(entity)
        return entity

    def allow_delete_hook(self, id: int) -> bool:
        return False  # Do not delete log
