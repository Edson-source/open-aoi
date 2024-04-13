from datetime import datetime
from sqlalchemy import select

from open_aoi.models import CameraModel, AccessorModel, InspectionProfileModel
from open_aoi.controllers import Controller


class CameraController(Controller):
    _model = CameraModel

    def create(
        self, title: str, description: str, ip_address: str, accessor: AccessorModel
    ) -> CameraModel:
        obj = CameraModel(
            title=title,
            description=description,
            ip_address=ip_address,
            created_by=accessor,
            created_at=datetime.now(),
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(InspectionProfileModel)
            .where(InspectionProfileModel.camera_id == id)
            .exists()
        ).scalar()
