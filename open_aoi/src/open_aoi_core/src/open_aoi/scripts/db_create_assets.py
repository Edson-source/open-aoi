"""Scripts create system wide known records in DB"""

from dotenv import load_dotenv

assert load_dotenv(".env")

from sqlalchemy.orm import Session

from open_aoi.models import *
from open_aoi.enums import *
from open_aoi.settings import (
    AOI_ADMINISTRATOR_INITIAL_PASSWORD,
    AOI_OPERATOR_INITIAL_PASSWORD,
)

if __name__ == "__main__":
    with Session(engine) as session:
        # Defect types
        dt_missing_component = DefectTypeModel(
            title="Missing component",
            description="Component is present on template, but is missing on tested image.",
        )

        dt_wrong_component_orientation = DefectTypeModel(
            title="Wrong component orientation",
            description="Component orientation is different against template.",
        )

        dt_typography = DefectTypeModel(
            title="Typografy",
            description="Typografy quality issues.",
        )

        # Roles
        r_operator = RoleModel(
            id=RoleEnum.OPERATOR.value,
            allow_system_view=True,
            allow_inspection_log_view=True,
            allow_inspection_details_view=True,
            allow_inspection_flow_control=True,
            allow_accessor_operations=False,
            allow_device_operations=False,
            allow_inspection_profile_operations=False,
            allow_system_operations=False,
            allow_statistics_view=False,
        )

        r_administrator = RoleModel(
            id=RoleEnum.ADMINISTRATOR.value,
            allow_system_view=True,
            allow_inspection_log_view=True,
            allow_inspection_details_view=True,
            allow_inspection_flow_control=True,
            allow_accessor_operations=True,
            allow_device_operations=True,
            allow_inspection_profile_operations=True,
            allow_system_operations=True,
            allow_statistics_view=True,
        )

        # Accessors
        a_operator = AccessorModel(
            id=AccessorEnum.OPERATOR.value,
            username="operator",
            title="Operator (default)",
            description="Operator is capable of basic sytem control including inspection requests.",
            role_id=RoleEnum.OPERATOR.value,
            hash=AccessorModel._hash_password(AOI_OPERATOR_INITIAL_PASSWORD),
        )
        a_administrator = AccessorModel(
            id=AccessorEnum.ADMINISTRATOR.value,
            username="administrator",
            title="Administrator (default)",
            description="Administrator is granted full access to system including security section and inspection configuration.",
            role_id=RoleEnum.ADMINISTRATOR.value,
            hash=AccessorModel._hash_password(AOI_ADMINISTRATOR_INITIAL_PASSWORD),
        )

        session.add_all(
            [
                dt_missing_component,
                dt_wrong_component_orientation,
                dt_typography,
                r_operator,
                r_administrator,
                a_operator,
                a_administrator,
            ]
        )
        session.commit()
