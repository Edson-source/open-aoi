from sqlalchemy import select
from sqlalchemy.orm import Session

from open_aoi.controllers import Controller
from open_aoi.models import DefectTypeModel, ControlHandlerModel


class DefectTypeController(Controller):
    _model = DefectTypeModel

    @classmethod
    def allow_delete_hook(cls, session: Session, id: int) -> bool:
        return not session.query(
            select(ControlHandlerModel)
            .where(ControlHandlerModel.defect_type_id == id)
            .exists()
        ).scalar()

    @classmethod
    def create(cls, title: str, description: str):
        with Session(cls.engine) as session:
            obj = DefectTypeModel(
                title=title,
                description=description,
            )
            session.add(obj)
            session.commit()
            return obj
