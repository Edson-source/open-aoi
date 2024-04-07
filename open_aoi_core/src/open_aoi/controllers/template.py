from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from PIL import Image

from open_aoi.models import (
    CameraModel,
    TemplateModel,
    AccessorModel,
    InspectionProfileModel,
)
from open_aoi.controllers import Controller


class TemplateController(Controller):
    _model = TemplateModel

    def create(
        self, title: str, image_blob: str, accessor: AccessorModel
    ) -> CameraModel:
        obj = TemplateModel(
            title=title,
            image_blob=image_blob,
            created_by=accessor,
            created_at=datetime.now(),
        )
        self.session.add(obj)
        return obj

    def allow_delete_hook(self, id: int) -> bool:
        return not self.session.query(
            select(InspectionProfileModel)
            .where(InspectionProfileModel.template_id == id)
            .exists()
        ).scalar()

    def list_nested(self) -> List[TemplateModel]:
        return (
            self.session.query(self._model)
            .options(joinedload(TemplateModel.control_zone_list))
            .options(joinedload(TemplateModel.inspection_profile_list))
            .all()
        )

    def post_delete_hook(self, obj: TemplateModel):
        if obj.is_valid:
            obj.destroy_image()

    test_store_connection = _model.test_store_connection
