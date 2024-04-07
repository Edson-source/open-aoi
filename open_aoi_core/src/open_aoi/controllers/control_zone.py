from typing import List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi.controllers import Controller
from open_aoi.models import (
    TemplateModel,
    ControlTargetModel,
    ControlZoneModel,
    AccessorModel,
)


class ControlZoneController(Controller):
    _model = ControlZoneModel

    def create(
        self,
        title: str,
        template: TemplateModel,
        accessor: AccessorModel,
    ) -> ControlZoneModel:
        obj = ControlZoneModel(
            title=title, template=template, created_by=accessor, created_at=datetime.now(), rotation=0
        )
        self.session.add(obj)
        return obj

    def list_nested(self) -> List[ControlZoneModel]:
        return (
            self.session.query(self._model)
            .options(joinedload(ControlZoneModel.cc))
            .options(joinedload(ControlZoneModel.control_target_list))
            .all()
        )

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(ControlTargetModel)
            .where(ControlTargetModel.control_zone_id == id)
            .exists()
        ).scalar()
