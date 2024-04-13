from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from open_aoi.models import (
    InspectionProfileModel,
    InspectionModel,
)
from open_aoi.controllers import Controller


class InspectionController(Controller):
    _model = InspectionModel

    def create(
        self,
        inspection_profile: InspectionProfileModel,
        image_blob: Optional[str] = None,
    ) -> InspectionModel:
        obj = InspectionModel(
            inspection_profile=inspection_profile,
            image_blob=image_blob,
            created_at=datetime.now(),
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return False  # Prevent log delete

    def list_nested(self) -> List[InspectionModel]:
        return (
            self.session.query(self._model)
            .options(joinedload(InspectionModel.inspection_log_list))
            .options(joinedload(InspectionModel.inspection_profile))
            .all()
        )

    test_store_connection = _model.test_store_connection
