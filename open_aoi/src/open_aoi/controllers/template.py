from sqlalchemy.orm import Session
from datetime import datetime

from open_aoi.models import CameraModel, TemplateModel, AccessorModel
from open_aoi.controllers import Controller


class TemplateController(Controller):
    _model = TemplateModel

    @classmethod
    def create(
        cls, title: str, image_blob: str, accessor: AccessorModel
    ) -> CameraModel:
        with Session(cls.engine) as session:
            obj = TemplateModel(
                title=title,
                image_blob=image_blob,
                created_by=accessor,
                created_at=datetime.now(),
            )
            session.add(obj)
            session.commit()
            return obj
