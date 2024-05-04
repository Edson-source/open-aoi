from typing import Optional

from sqlalchemy import select

from open_aoi_core.controllers import Controller
from open_aoi_core.exceptions import SystemIntegrityException
from open_aoi_core.models import (
    CameraModel,
    AccessorModel,
    InspectionProfileModel,
    InspectionModel,
)

class CameraController(Controller):
    _model = CameraModel

    def create(
        self,
        title: str,
        description: str,
        ip_address: str,
        accessor: AccessorModel,
        io_pin_trigger: Optional[int] = None,
        io_pin_accept: Optional[int] = None,
        io_pin_reject: Optional[int] = None,
    ) -> CameraModel:
        """
        Create camera entity. If trigger pin is defined, accept and reject pins must also be defined.
        - raise: SystemIntegrityException if pin definition logic is violated.
        """
        try:
            assert (io_pin_trigger is None) or (
                io_pin_accept is not None and io_pin_reject is not None
            )
        except AssertionError as e:
            raise SystemIntegrityException(
                "Trigger pin is defined. Accept and reject pins must also be defined."
            ) from e

        entity = CameraModel(
            title=title,
            description=description,
            ip_address=ip_address,
            created_by=accessor,
            io_pin_trigger=io_pin_trigger,
            io_pin_accept=io_pin_accept,
            io_pin_reject=io_pin_reject,
        )
        self.session.add(entity)
        return entity

    def retrieve_by_io_pin_trigger(self, io_pin: int) -> Optional[CameraModel]:
        """Retrieve camera by related I/O trigger pin"""
        return (
            self.session.query(self._model)
            .filter(
                self._model.io_pin_trigger == io_pin,
            )
            .one_or_none()
        )

    def allow_delete_hook(self, id: int) -> bool:
        """Ensure no inspection profiles or inspection records are related to this camera"""
        return not (
            self.session.query(
                select(InspectionProfileModel)
                .where(InspectionProfileModel.camera_id == id)
                .exists()
            ).scalar()
            or self.session.query(
                select(InspectionModel).where(InspectionModel.camera_id == id).exists()
            ).scalar()
        )
