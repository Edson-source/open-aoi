from typing import Optional

from sqlalchemy import select

from open_aoi_core.models import CameraModel, AccessorModel, InspectionProfileModel
from open_aoi_core.controllers import Controller


class CameraController(Controller):
    _model = CameraModel

    def create(
        self,
        title: str,
        description: str,
        ip_address: str,
        accessor: AccessorModel,
        io_pin: Optional[int] = None,
    ) -> CameraModel:
        obj = CameraModel(
            title=title,
            description=description,
            ip_address=ip_address,
            created_by=accessor,
            io_pin_trigger=io_pin,
        )
        self.session.add(obj)
        return obj

    def retrieve_by_io_pin(self, io_pin: int) -> CameraModel:
        return (
            self.session.query(self._model)
            .filter(
                self._model.io_pin_trigger == io_pin,
            )
            .one_or_none()
        )

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(InspectionProfileModel)
            .where(InspectionProfileModel.camera_id == id)
            .exists()
        ).scalar()
