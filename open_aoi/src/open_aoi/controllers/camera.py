from datetime import datetime
from sqlalchemy.orm import Session

from open_aoi.models import (
    CameraModel,
    AccessorModel,
)
from open_aoi.controllers import Controller


class CameraController(Controller):
    _model = CameraModel

    @classmethod
    def create(
        cls, title: str, description: str, ip_address: str, accessor: AccessorModel
    ) -> CameraModel:
        with Session(cls.engine) as session:
            obj = CameraModel(
                title=title,
                description=description,
                ip_address=ip_address,
                created_by=accessor,
                created_at=datetime.now(),
            )
            session.add(obj)
            session.commit()
            return obj
