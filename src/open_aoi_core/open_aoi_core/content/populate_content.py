"""Script upload default content to database and publish default inspection modules"""

from sqlalchemy.orm import Session

from open_aoi_core.models import *
from open_aoi_core.constants import *
from open_aoi_core.controllers.inspection_handler import InspectionHandlerController
from open_aoi_core.settings import (
    AOI_ADMINISTRATOR_INITIAL_PASSWORD,
    AOI_OPERATOR_INITIAL_PASSWORD,
    DEFAULT_DEFECT_TYPES,
    DEFAULT_MODULES,
)

if __name__ == "__main__":
    metadata_obj.drop_all(engine)
    metadata_obj.create_all(engine)

    with Session(engine) as session:
        inspection_handler_controller = InspectionHandlerController(session)

        # Defect types
        defect_types = {}
        for key, value in DEFAULT_DEFECT_TYPES.items():
            defect_type = DefectTypeModel(
                title=value["title"],
                description=value["description"],
            )
            defect_types[key] = defect_type
            session.add(defect_type)

        # Roles
        session.add(
            RoleModel(
                id=SystemRole.OPERATOR,
                allow_system_view=True,
                allow_inspection_view=True,
                allow_inspection_control=True,
                allow_system_operations=False,
                allow_statistics_view=False,
            )
        )

        session.add(
            RoleModel(
                id=SystemRole.ADMINISTRATOR,
                allow_system_view=True,
                allow_inspection_view=True,
                allow_inspection_control=True,
                allow_system_operations=True,
                allow_statistics_view=True,
            )
        )

        # Accessors
        session.add(
            AccessorModel(
                username="operator",
                title="Operator (default)",
                description="Operator is capable of basic sytem control including inspection requests.",
                role_id=SystemRole.OPERATOR,
                hash=AccessorModel._hash_password(AOI_OPERATOR_INITIAL_PASSWORD),
            )
        )
        session.add(
            AccessorModel(
                username="administrator",
                title="Administrator (default)",
                description="Administrator is granted full access to system including security section and inspection configuration.",
                role_id=SystemRole.ADMINISTRATOR,
                hash=AccessorModel._hash_password(AOI_ADMINISTRATOR_INITIAL_PASSWORD),
            )
        )

        for key, value in DEFAULT_MODULES.items():
            with open(key, "rb") as f:
                source = f.read()
                inspection_handler = inspection_handler_controller.create(
                    value["title"], defect_types[value["type"]]
                )
                inspection_handler.publish_source(source)
            session.add(inspection_handler)

        session.commit()
