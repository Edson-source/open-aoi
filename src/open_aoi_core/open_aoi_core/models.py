from datetime import datetime
from typing import Optional, List
import ipaddress

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    DeclarativeBase,
    relationship,
    validates,
)
from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    DateTime,
    func,
    Boolean,
    Integer,
    MetaData,
    Text,
)

from open_aoi_core.settings import (
    MYSQL_DATABASE,
    MYSQL_PASSWORD,
    MYSQL_USER,
    MYSQL_HOST,
    MYSQL_PORT,
)
from open_aoi_core.constants import SystemLimit
from open_aoi_core.mixins.authentication import DatabaseAuthenticationMixin, SessionAuthenticationMixin
from open_aoi_core.mixins.image_source import (
    TemplateImageSourceMixin,
    InspectionImageSourceMixin,
)
from open_aoi_core.mixins.module_source import ModuleSourceMixin


metadata_obj = MetaData()
engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)


class Base(DeclarativeBase):
    metadata = metadata_obj

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# User management related schemas
class RoleModel(Base):
    """Define accessor rights for role based authorization model"""

    __tablename__ = "Role"

    # General access to the system
    allow_system_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow results view
    allow_inspection_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow triggering inspection
    allow_inspection_control: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow operations of accessors (create, modify, etc)
    allow_accessor_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow operations on devices
    allow_device_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow system operations
    allow_system_operations: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    # Allow statistics view
    allow_statistics_view: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )

    accessor_list: Mapped[List["AccessorModel"]] = relationship(back_populates="role")


class AccessorModel(Base, DatabaseAuthenticationMixin, SessionAuthenticationMixin):
    """Accessor is an entity that interact with the system and is granted rights to perform operations"""

    __tablename__ = "Accessor"

    # User name is used for login purposes
    username: Mapped[str] = mapped_column(
        String(SystemLimit.TITLE_LENGTH), nullable=False
    )
    # Public title and description of accessor
    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(SystemLimit.DESCRIPTION_LENGTH), nullable=False
    )

    # Related rights
    role_id: Mapped[int] = mapped_column(ForeignKey("Role.id"), nullable=False)
    role: Mapped["RoleModel"] = relationship()

    # Hashed password
    hash: Mapped[str] = mapped_column(String(60), nullable=False)


# Inspection related schemas
class DefectTypeModel(Base):
    """Define system wide known defect types"""

    __tablename__ = "DefectType"

    # Public description
    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(SystemLimit.DESCRIPTION_LENGTH), nullable=False
    )

    # Related control handlers
    control_handler_list: Mapped[List["ControlHandlerModel"]] = relationship(
        back_populates="defect_type"
    )


class ControlHandlerModel(Base, ModuleSourceMixin):
    """Database representation of control handler. Used to store blob reference and control handler metadata"""

    __tablename__ = "ControlHandler"

    # Public description
    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(SystemLimit.DESCRIPTION_LENGTH), nullable=False
    )

    # If null, should not be used!
    blob: Mapped[str] = mapped_column(
        String(SystemLimit.BLOB_UID_LENGTH), nullable=True
    )

    # Related defect, that is handled by that control handler
    defect_type_id: Mapped[int] = mapped_column(
        ForeignKey("DefectType.id"), nullable=False
    )
    defect_type: Mapped["DefectTypeModel"] = relationship(
        back_populates="control_handler_list"
    )

    # Related control targets
    control_target_list: Mapped[List["ControlTargetModel"]] = relationship(
        back_populates="control_handler"
    )


class ControlTargetModel(Base):
    """
    Helper object to map control handler to the control zone.
    Multiple control targets are allowed for single control zone.
    """

    __tablename__ = "ControlTarget"

    # Control handler
    control_handler_id: Mapped[int] = mapped_column(
        ForeignKey("ControlHandler.id"), nullable=False
    )
    control_handler: Mapped["ControlHandlerModel"] = relationship(
        back_populates="control_target_list"
    )

    # Control zone
    control_zone_id: Mapped[int] = mapped_column(
        ForeignKey("ControlZone.id"), nullable=False
    )
    control_zone: Mapped["ControlZoneModel"] = relationship(
        back_populates="control_target_list"
    )


class ConnectedComponentModel(Base):
    """
    Describe coordinates for control zone (where to expect the defect)
    """

    __tablename__ = "ConnectedComponent"

    # Coordinates in style of OpenCV statistics for connected components
    stat_left: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_top: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_width: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Related control zone
    control_zone_id: Mapped[int] = mapped_column(
        ForeignKey("ControlZone.id"), nullable=False
    )
    control_zone: Mapped["ControlZoneModel"] = relationship(back_populates="cc")


class ControlZoneModel(Base):
    """
    Small zone on image (tested and template) where defect is expected. Coordinates are identified with
    related connected component. Rotation parameter may be applied. Related control handler is identified via
    helper control target object.
    """

    __tablename__ = "ControlZone"

    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)

    # Related template
    template_id: Mapped[int] = mapped_column(ForeignKey("Template.id"), nullable=False)
    template: Mapped["TemplateModel"] = relationship(back_populates="control_zone_list")

    # Related connected component and rotation
    cc: Mapped["ConnectedComponentModel"] = relationship(
        back_populates="control_zone", cascade="all, delete-orphan"
    )
    rotation: Mapped[float] = mapped_column(Numeric(precision=10, scale=2))

    # Related control targets (lead to control handler)
    control_target_list: Mapped[List["ControlTargetModel"]] = relationship(
        back_populates="control_zone",  # Cascade -prevent delete if any target use this control zone
    )

    # Accessor relation for log purposes
    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()


class InspectionLogModel(Base):
    """
    Helper to map defect type that was found to control zone. Multiple control logs are allowed.
    """

    __tablename__ = "ControlLog"

    # Related control target
    control_target_id: Mapped[int] = mapped_column(
        ForeignKey("ControlTarget.id"), nullable=False
    )
    control_target: Mapped["ControlTargetModel"] = relationship()

    # Control results (for concrete control zone)
    passed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    log: Mapped[str] = mapped_column(String(200), nullable=True)

    # Related inspection
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("Inspection.id"), nullable=False
    )
    inspection: Mapped["InspectionModel"] = relationship(
        back_populates="inspection_log_list"
    )


class InspectionModel(Base, InspectionImageSourceMixin):
    """information about conducted inspection"""

    __tablename__ = "Inspection"

    blob: Mapped[str] = mapped_column(
        String(SystemLimit.BLOB_UID_LENGTH), nullable=False
    )

    # Related profile
    inspection_profile_id: Mapped[int] = mapped_column(
        ForeignKey("InspectionProfile.id"), nullable=False
    )
    inspection_profile: Mapped["InspectionProfileModel"] = relationship(
        back_populates="inspection_list"
    )

    # List of related logs
    inspection_log_list: Mapped[List["InspectionLogModel"]] = relationship(
        back_populates="inspection"
    )

    # Related camera
    camera_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("Camera.id"), nullable=True
    )
    camera: Mapped[Optional["CameraModel"]] = relationship()

    @property
    def overall_passed(self):
        return all(
            [inspection_log.passed for inspection_log in self.inspection_log_list]
        )


class TemplateModel(Base, TemplateImageSourceMixin):
    """
    Main reference image. Aggregate all control zones.
    """

    __tablename__ = "Template"

    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)

    blob: Mapped[str] = mapped_column(String(100), nullable=True)

    # Related control zones
    control_zone_list: Mapped[List["ControlZoneModel"]] = relationship(
        back_populates="template",  # Delete cascade - prevent if control zone use template
    )

    # Related inspection profiles
    inspection_profile_list: Mapped["InspectionProfileModel"] = relationship(
        back_populates="template",  # Cascade should prevent delete operation if profiles are found
    )

    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()


class CameraModel(Base):
    """
    Represent available cameras (devices)
    """

    __tablename__ = "Camera"

    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(SystemLimit.DESCRIPTION_LENGTH), nullable=False
    )

    ip_address: Mapped[str] = mapped_column(String(15), nullable=False)

    # I/O logic. If trigger pin is null, it will not be triggering inspection
    io_pin_trigger: Mapped[int] = mapped_column(Integer(), nullable=True)
    io_pin_accept: Mapped[int] = mapped_column(Integer(), nullable=True)
    io_pin_reject: Mapped[int] = mapped_column(Integer(), nullable=True)

    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()

    @validates("ip_address")
    def validate_email(self, key, value):
        if not ipaddress.ip_address(value):
            raise ValueError("IP address is not valid.")
        return value


class InspectionProfileModel(Base):
    """
    Concrete instance of desired test configuration (template with device)
    """

    __tablename__ = "InspectionProfile"

    # Activation flag. If set related I/O pin will trigger inspection. Inactive profiles are not
    # available for manual trigger
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Public description
    title: Mapped[str] = mapped_column(String(SystemLimit.TITLE_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(
        String(SystemLimit.DESCRIPTION_LENGTH), nullable=False
    )

    # Environment variables for control handler
    environment: Mapped[str] = mapped_column(Text(), nullable=True)

    # Product identification
    identification_code: Mapped[str] = mapped_column(
        String(SystemLimit.IDENTIFICATION_CODE_LENGTH), nullable=False
    )

    # Related template
    template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("Template.id"), nullable=True
    )
    template: Mapped[Optional["TemplateModel"]] = relationship()

    # Related inspection records
    inspection_list: Mapped[List["InspectionModel"]] = relationship(
        back_populates="inspection_profile"
    )

    created_by_accessor_id: Mapped[int] = mapped_column(
        ForeignKey("Accessor.id"), nullable=False
    )
    created_by: Mapped["AccessorModel"] = relationship()
