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

    def retrieve_by_camera(
        self, camera_id: int
    ) -> Optional[InspectionProfileModel]:
        """Retrieve default inspection profile for a camera"""
        from open_aoi_core.models import CameraModel
        return (
            self.session.query(self._model)
            .join(CameraModel, CameraModel.default_inspection_profile_id == self._model.id)
            .filter(
                and_(
                    CameraModel.id == camera_id,
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

    def activate(self, profile: InspectionProfileModel):
        """Activates profile and links it to the default camera"""
        profile.is_active = True
        
        # Importamos o modelo da Câmera (assim como você fez no retrieve_by_camera)
        from open_aoi_core.models import CameraModel
        
        # Buscamos a primeira câmera cadastrada no sistema (ou filtre por ID == 1 se preferir)
        camera = self.session.query(CameraModel).first()
        
        # Se a câmera existir, atribuímos o ID deste perfil recém-ativado a ela
        if camera:
            camera.default_inspection_profile_id = profile.id
            # Nota: Não usamos self.session.commit() aqui porque o Open-AOI 
            # já faz o commit automaticamente no final da requisição da API.

    def deactivate(self, profile: InspectionProfileModel):
        """Deactivates profile and unlinks it from the camera if it was the default"""
        profile.is_active = False
        
        from open_aoi_core.models import CameraModel
        
        # Se o perfil for desativado, removemos ele da câmera para não bugar a inspeção
        camera = self.session.query(CameraModel).filter(
            CameraModel.default_inspection_profile_id == profile.id
        ).first()
        
        if camera:
            camera.default_inspection_profile_id = None
            
            
   #  def deactivate(self, profile: InspectionProfileModel):
   #      """Deactivates profile"""
   #      profile.is_active = False

   #  def list_active(self) -> List[InspectionProfileModel]:
   #      """List active profiles"""
   #      return self.session.query(self._model).filter(self._model.is_active == True).all()
