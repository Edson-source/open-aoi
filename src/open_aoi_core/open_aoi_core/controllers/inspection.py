from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from open_aoi_core.models import (
    InspectionProfileModel,
    InspectionModel,
)
from open_aoi_core.controllers import Controller


class InspectionController(Controller):
    _model = InspectionModel

    def create(
        self,
        inspection_profile: InspectionProfileModel,
        image_blob: Optional[str] = None,
    ) -> InspectionModel:
        """Create inspection"""
        entity = InspectionModel(
            inspection_profile=inspection_profile,
            image_blob=image_blob,
        )
        self.session.add(entity)
        return entity

    def allow_delete_hook(self, id: int) -> bool:
        return False  # Prevent log delete

    def list_nested(self) -> List[InspectionModel]:
        """Return list of inspections with related log and profiles"""
        return (
            self.session.query(self._model)
            .options(joinedload(InspectionModel.inspection_log_list))
            .options(joinedload(InspectionModel.inspection_profile))
            .all()
        )

    test_minio_connection = _model.test_minio_connection
