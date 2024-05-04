from typing import List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    TemplateModel,
    InspectionTargetModel,
    InspectionZoneModel,
    AccessorModel,
)


class InspectionZoneController(Controller):
    _model = InspectionZoneModel

    def create(
        self,
        title: str,
        template: TemplateModel,
        accessor: AccessorModel,
    ) -> InspectionZoneModel:
        """Create inspection zone"""
        entity = InspectionZoneModel(
            title=title,
            template=template,
            created_by=accessor,
            rotation=0,  # TODO: real rotation
        )
        self.session.add(entity)
        return entity

    def list_nested(self) -> List[InspectionZoneModel]:
        """List inspection zones with related connected components and targets"""
        return (
            self.session.query(self._model)
            .options(joinedload(InspectionZoneModel.cc))
            .options(joinedload(InspectionZoneModel.inspection_target_list))
            .all()
        )

    def allow_delete_hook(self, id: int) -> bool:
        """Allow delete if no inspection target refer the zone"""
        return not self.session.query(
            select(InspectionTargetModel)
            .where(InspectionTargetModel.inspection_zone_id == id)
            .exists()
        ).scalar()
