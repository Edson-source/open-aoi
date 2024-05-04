from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from open_aoi_core.models import (
    CameraModel,
    TemplateModel,
    AccessorModel,
    InspectionProfileModel,
    InspectionZoneModel,
)
from open_aoi_core.controllers import Controller


class TemplateController(Controller):
    _model = TemplateModel

    def create(
        self, title: str, accessor: AccessorModel, image_blob: Optional[str] = None
    ) -> CameraModel:
        obj = TemplateModel(
            title=title,
            image_blob=image_blob,
            created_by=accessor,
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        any_inspection_profile = self.session.query(
            select(InspectionProfileModel)
            .where(InspectionProfileModel.template_id == id)
            .exists()
        ).scalar()
        any_inspection_zone = self.session.query(
            select(InspectionZoneModel).where(InspectionZoneModel.template_id == id).exists()
        ).scalar()
        return not (any_inspection_profile or any_inspection_zone)

    def list_nested(self) -> List[TemplateModel]:
        return (
            self.session.query(self._model)
            .options(joinedload(TemplateModel.inspection_zone_list))
            .options(joinedload(TemplateModel.inspection_profile_list))
            .all()
        )

    def post_delete_hook(self, obj: TemplateModel):
        if obj.has_source_blob:
            obj.destroy_image()

    test_store_connection = _model.test_store_connection
