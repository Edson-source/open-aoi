from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from open_aoi.controllers import Controller
from open_aoi.models import (
    Base,
    ControlHandlerModel,
    DefectTypeModel,
    ControlTargetModel,
)


class ControlHandlerController(Controller):
    _model = ControlHandlerModel

    @classmethod
    def create(
        cls, title: str, description: str, defect_type: DefectTypeModel
    ) -> ControlHandlerModel:
        """
        Create blank controller representation, should be
        populated with content separately (due to UI file upload util)
        """
        with Session(cls.engine) as session:
            obj = ControlHandlerModel(
                title=title, description=description, defect_type=defect_type
            )
            session.add(obj)
            session.commit()
            return obj

    @classmethod
    def list_nested(cls) -> List[ControlHandlerModel]:
        with Session(cls.engine) as session:
            return (
                session.query(cls._model)
                .options(joinedload(ControlHandlerModel.defect_type))
                .all()
            )

    @classmethod
    def allow_delete_hook(cls, session: Session, id: int) -> bool:
        return not session.query(
            select(ControlTargetModel)
            .where(ControlTargetModel.control_handler_id == id)
            .exists()
        ).scalar()

    @classmethod
    def post_delete_hook(cls, obj: ControlHandlerModel):
        obj.destroy_source()

    @classmethod
    def publish_source(cls, obj: ControlHandlerModel, content: bytes):
        obj.handler_blob = obj.publish_source(content)
        with Session(cls.engine) as session:
            session.add(obj)
            session.commit()

    @classmethod
    def materialize_for_download(cls, obj: ControlHandlerModel) -> bytes:
        module = obj.materialize_source()
        return module._source

    validate_source = _model.validate_source
    test_store_connection = _model.test_store_connection
