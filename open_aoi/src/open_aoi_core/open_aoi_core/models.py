from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    DateTime,
    func,
    Boolean,
    Integer,
    MetaData,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

from open_aoi.settings import MYSQL_DATABASE, MYSQL_PASSWORD, MYSQL_USER, MYSQL_PORT
from open_aoi.enums import RoleEnum, AccessorEnum
from open_aoi.mixins.authentication import AuthMixin, SessionCredentialsMixin
from open_aoi.mixins.image_source import (
    TemplateImageSourceMixin,
    InspectionImageSourceMixin,
)
from open_aoi.mixins.module_source import ModuleSourceMixin


CODE_LIMIT = 100
TITLE_LIMIT = 200
DESCRIPTION_LIMIT = 500


metadata_obj = MetaData()
engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@localhost:{MYSQL_PORT}/{MYSQL_DATABASE}"
)


class Base(DeclarativeBase):
    pass


class RoleModel(Base):
    """Define accessor rights"""

    __tablename__ = "Role"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )

    allow_system_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_inspection_log_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_inspection_details_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_inspection_flow_control: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_accessor_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_device_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_inspection_profile_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_system_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    allow_statistics_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )

    accessor_list: Mapped[List["AccessorModel"]] = relationship(back_populates="role")
    registry = RoleEnum


class AccessorModel(Base, AuthMixin, SessionCredentialsMixin):
    __tablename__ = "Accessor"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )

    username: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_LIMIT), nullable=False)

    role_id: Mapped[int] = mapped_column(ForeignKey("Role.id"), nullable=False)
    role: Mapped["RoleModel"] = relationship()

    hash: Mapped[str] = mapped_column(String(60), nullable=False)
    registry = AccessorEnum


class DefectTypeModel(Base):
    """Define system wide known error types"""

    __tablename__ = "DefectType"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_LIMIT), nullable=False)

    control_handler_list: Mapped[List["ControlHandlerModel"]] = relationship(
        back_populates="defect_type"
    )


class ControlHandlerModel(Base, ModuleSourceMixin):
    """Database representation of control handler"""

    __tablename__ = "ControlHandler"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_LIMIT), nullable=False)

    handler_blob: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # If null, should not be used!

    control_target_list: Mapped[List["ControlTargetModel"]] = relationship(
        back_populates="control_handler"
    )

    defect_type_id: Mapped[int] = mapped_column(
        ForeignKey("DefectType.id"), nullable=False
    )
    defect_type: Mapped["DefectTypeModel"] = relationship(
        back_populates="control_handler_list"
    )


class ControlTargetModel(Base):
    """
    Helper object to map control handler to the control zone (control handler is unique).
    Multiple control targets are allowed for single control zone.
    """

    __tablename__ = "ControlTarget"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    control_handler_id: Mapped[int] = mapped_column(
        ForeignKey("ControlHandler.id"), nullable=False
    )
    control_handler: Mapped["ControlHandlerModel"] = relationship(
        back_populates="control_target_list"
    )

    control_zone_id: Mapped[int] = mapped_column(
        ForeignKey("ControlZone.id"), nullable=False
    )
    control_zone: Mapped["ControlZoneModel"] = relationship(
        back_populates="control_target_list"
    )


class ConnectedComponentModel(Base):
    """
    Location description for control zone
    """

    __tablename__ = "ConnectedComponent"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    stat_left: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_top: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_width: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_height: Mapped[int] = mapped_column(Integer, nullable=False)

    control_zone_id: Mapped[int] = mapped_column(
        ForeignKey("ControlZone.id"), nullable=False
    )
    control_zone: Mapped["ControlZoneModel"] = relationship(back_populates="cc")


class ControlZoneModel(Base):
    """
    Small zone on template where related control handler is applied in order to detect defect type
    """

    __tablename__ = "ControlZone"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)

    template_id: Mapped[int] = mapped_column(ForeignKey("Template.id"), nullable=False)
    template: Mapped["TemplateModel"] = relationship(back_populates="control_zone_list")

    cc: Mapped["ConnectedComponentModel"] = relationship(
        back_populates="control_zone", cascade="all, delete-orphan"
    )

    rotation: Mapped[float] = mapped_column(Numeric(precision=10, scale=2))

    control_target_list: Mapped[List["ControlTargetModel"]] = relationship(
        back_populates="control_zone",  # Cascade -prevent delete if any target use this control zone
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()


class InspectionLogModel(Base):
    """
    Helper to map defect type that was found to control zone. Multiple control logs are allowed.
    """

    __tablename__ = "ControlLog"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    control_target_id: Mapped[int] = mapped_column(
        ForeignKey("ControlTarget.id"), nullable=False
    )
    control_target: Mapped["ControlTargetModel"] = relationship()
    passed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    log: Mapped[str] = mapped_column(String(200), nullable=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("Inspection.id"), nullable=False
    )
    inspection: Mapped["InspectionModel"] = relationship(
        back_populates="inspection_log_list"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InspectionModel(Base, InspectionImageSourceMixin):
    """
    Connect defect collection with template
    """

    __tablename__ = "Inspection"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    image_blob: Mapped[str] = mapped_column(String(100), nullable=False)

    inspection_profile_id: Mapped[int] = mapped_column(
        ForeignKey("InspectionProfile.id"), nullable=False
    )
    inspection_profile: Mapped["InspectionProfileModel"] = relationship(
        back_populates="inspection_list"
    )

    inspection_log_list: Mapped[List["InspectionLogModel"]] = relationship(
        back_populates="inspection"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def overall_passed(self):
        raise NotImplementedError()


class TemplateModel(Base, TemplateImageSourceMixin):
    """
    Main reference image. Aggregate control zones.
    """

    __tablename__ = "Template"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)

    image_blob: Mapped[str] = mapped_column(String(100), nullable=True)

    control_zone_list: Mapped[List["ControlZoneModel"]] = relationship(
        back_populates="template",  # Delete cascade - prevent if control zone use template
    )

    inspection_profile_list: Mapped["InspectionProfileModel"] = relationship(
        back_populates="template",  # Cascade should prevent delete operation if profiles are found
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()


class CameraModel(Base):
    """
    Represent available cameras
    """

    __tablename__ = "Camera"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_LIMIT), nullable=False)

    # TODO: insert validation ipv4
    ip_address: Mapped[str] = mapped_column(String(15), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()


class InspectionProfileModel(Base):
    """
    Concrete instance of desired test configuration
    """

    __tablename__ = "InspectionProfile"
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    title: Mapped[str] = mapped_column(String(TITLE_LIMIT), nullable=False)
    description: Mapped[str] = mapped_column(String(DESCRIPTION_LIMIT), nullable=False)

    identification_code: Mapped[str] = mapped_column(String(CODE_LIMIT), nullable=False)

    camera_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("Camera.id"), nullable=True
    )
    camera: Mapped[Optional["CameraModel"]] = relationship()

    template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("Template.id"), nullable=True
    )
    template: Mapped[Optional["TemplateModel"]] = relationship()

    inspection_list: Mapped[List["InspectionModel"]] = relationship(
        back_populates="inspection_profile"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()
