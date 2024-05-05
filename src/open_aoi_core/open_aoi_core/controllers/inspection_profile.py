from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from open_aoi_core.controllers import Controller
from open_aoi_core.models import (
    InspectionProfileModel,
    TemplateModel,
    AccessorModel,
    InspectionModel,
)


class InspectionProfileController(Controller):
    _model = InspectionProfileModel

    def create(
        self,
        title: str,
        description: str,
        identification_code: str,
        template: TemplateModel,
        accessor: AccessorModel,
        environment: Optional[str] = None,
    ) -> InspectionProfileModel:
        """
        Create blank controller representation, should be
        populated with content separately (due to UI file upload util)
        """
        entity = InspectionProfileModel(
            title=title,
            description=description,
            identification_code=identification_code,
            template=template,
            created_by=accessor,
            environment=environment,
        )
        self.session.add(entity)
        return entity

    def retrieve_by_identification_code(
        self, identification_code: str
    ) -> Optional[InspectionProfileModel]:
        """Retrieve inspection profile by related identification code. Profile should be active"""
        return (
            self.session.query(self._model)
            .filter(
                and_(
                    self._model.identification_code == identification_code,
                    self._model.is_active == True,
                )
            )
            .one_or_none()
        )

    def allow_delete_hook(self, id: int) -> bool:
        """Allow delete if no inspection refer to this profile"""
        return not self.session.query(
            select(InspectionModel)
            .where(InspectionModel.inspection_profile_id == id)
            .exists()
        ).scalar()

    def list_nested(self) -> List[InspectionProfileModel]:
        """List profiles with template"""
        return (
            self.session.query(self._model)
            .options(joinedload(InspectionProfileModel.template))
            .all()
        )

    def activate(self, profile: InspectionProfileModel):
        """Activates profile"""
        profile.is_active = True

    def deactivate(self, profile: InspectionProfileModel):
        """Deactivates profile"""
        profile.is_active = False

    def list_active(self) -> List[InspectionProfileModel]:
        """List active profiles"""
        return self.session.query(self._model).filter(self._model.is_active == True).all()
