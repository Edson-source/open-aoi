import logging
from typing import Optional
from functools import partial

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.models import TITLE_LIMIT, DESCRIPTION_LIMIT, InspectionProfileModel
from open_aoi_core.exceptions import AuthException, IntegrityError
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.camera import CameraController
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_core.models import TITLE_LIMIT, DESCRIPTION_LIMIT, CODE_LIMIT
from open_aoi_portal.common import (
    ACCESS_PAGE,
    INSPECTION_PROFILE_EDIT_PAGE,
    INSPECTION_PROFILE_CREATE_PAGE,
    inject_text_field,
    inject_header,
    get_session,
)

logger = logging.getLogger("ui.inspection_profile")


def get_view(node: Node):
    def view(profile_id: Optional[int] = None) -> Optional[RedirectResponse]:
        session = get_session()
        access_controller = AccessorController(session)
        camera_controller = CameraController(session)
        template_controller = TemplateController(session)
        inspection_profile_controller = InspectionProfileController(session)

        # -------------------
        # Handlers
        def _handle_push_profile():
            nonlocal inspection_profile
            try:
                assert profile_title.validate()
                assert profile_description.validate()
                assert profile_environment.validate()
                assert identification_code.validate()
                assert template_select.validate()
                assert camera_select.validate()
            except AssertionError:
                ui.notify("Some required parameters are missing", type="warning")
                return

            try:
                camera = camera_controller.retrieve(camera_select.value)
                template = template_controller.retrieve(template_select.value)
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to retrieve data from database!", type="negative")
                return

            if inspection_profile is None:
                try:
                    inspection_profile = inspection_profile_controller.create(
                        title=profile_title.value.strip(),
                        description=profile_description.value.strip(),
                        identification_code=identification_code.value.strip(),
                        camera=camera,
                        template=template,
                        accessor=accessor,
                        environment=profile_environment.value.strip(),
                    )
                    inspection_profile_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to create profile!", type="negative")
                    return
                ui.notify("New profile created", type="positive")
            else:
                try:
                    inspection_profile.environment = profile_environment.value.strip()
                    inspection_profile_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to update profile!", type="negative")
                    return
                ui.notify("Updated", type="positive")
            _inject_profile_list()

        def _handle_delete_profile(profile: InspectionProfileModel):
            try:
                inspection_profile_controller.delete(profile)
                inspection_profile_controller.commit()
            except IntegrityError as e:
                logger.exception(e)
                ui.notify(str(e), type="warning")
                return
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to push changes to database!", type="negative")
                return

            ui.notify("Profile deleted", type="positive")
            if inspection_profile is not None and profile.id == inspection_profile.id:
                ui.open(INSPECTION_PROFILE_CREATE_PAGE)
                return
            _inject_profile_list()

        def _handle_edit_profile(profile: InspectionProfileModel):
            ui.open(INSPECTION_PROFILE_EDIT_PAGE.format(profile_id=profile.id))

        def _handle_activate_profile(profile: InspectionProfileModel):
            try:
                inspection_profile_controller.activate(profile)
                inspection_profile_controller.commit()
            except IntegrityError as e:
                logger.exception(e)
                ui.notify(str(e), type="warning")
                return
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to push changes to database!", type="negative")
                return
            _inject_profile_list()

        def _handle_deactivate_profile(profile: InspectionProfileModel):
            try:
                inspection_profile_controller.deactivate(profile)
                inspection_profile_controller.commit()
            except IntegrityError as e:
                logger.exception(e)
                ui.notify(str(e), type="warning")
                return
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to push changes to database!", type="negative")
                return
            _inject_profile_list()

        # Local injections
        def _inject_profile_list():
            profile_list_container.clear()
            profile_list = inspection_profile_controller.list_nested()

            with profile_list_container:
                if len(profile_list):
                    for profile in profile_list:
                        with ui.item(f"{profile.title}. {profile.description}").props(
                            "clickable"
                        ):
                            with ui.item_section():
                                with ui.row():
                                    ui.space()
                                    ui.button(
                                        (
                                            "Deactivate"
                                            if profile.is_active
                                            else "Activate"
                                        ),
                                        color="warning" if profile.is_active else None,
                                        on_click=(
                                            partial(_handle_deactivate_profile, profile)
                                            if profile.is_active
                                            else partial(
                                                _handle_activate_profile, profile
                                            )
                                        ),
                                    ).props("size=sm")
                                    ui.button(
                                        "Edit",
                                        on_click=partial(_handle_edit_profile, profile),
                                    ).props("size=sm")
                                    ui.button(
                                        "Remove",
                                        on_click=partial(
                                            _handle_delete_profile, profile
                                        ),
                                        color="negative",
                                    ).props("size=sm")
                else:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No profiles to show**")

        # -------------------

        try:
            accessor = access_controller.identify_session_accessor(app.storage.user)
        except AuthException:
            return RedirectResponse(ACCESS_PAGE)

        inject_header()

        try:
            if profile_id is None:
                inspection_profile = None
            else:
                inspection_profile = inspection_profile_controller.retrieve(profile_id)
            camera_list = dict(
                [(obj.id, obj.title) for obj in camera_controller.list()]
            )
            template_list = dict(
                [(obj.id, obj.title) for obj in template_controller.list()]
            )
        except Exception as e:
            logger.exception(e)
            return RedirectResponse(INSPECTION_PROFILE_CREATE_PAGE)

        with ui.column().classes("w-full"):
            ui.markdown("#### **Inspection profile**")
            ui.markdown("##### **Create profile**")
            profile_title = inject_text_field(
                "Profile title", "Enter anything...", TITLE_LIMIT
            )
            profile_title.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_title.set_value(inspection_profile.title)

            profile_description = inject_text_field(
                "Profile description", "Enter anything...", DESCRIPTION_LIMIT
            )
            profile_description.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_description.set_value(inspection_profile.description)

            camera_select = ui.select(
                camera_list,
                label="Camera",
                clearable=True,
                validation={"Camera is required": lambda value: value is not None},
            ).classes("w-full")
            camera_select.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                camera_select.set_value(inspection_profile.camera_id)

            identification_code = inject_text_field(
                "Product identification code (barcode value)",
                "Enter code value...",
                CODE_LIMIT,
            )
            identification_code.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                identification_code.set_value(inspection_profile.identification_code)

            template_select = ui.select(
                template_list,
                label="Template",
                clearable=True,
                validation={"Template is required": lambda value: value is not None},
            ).classes("w-full")
            template_select.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                template_select.set_value(inspection_profile.template_id)

            profile_environment = ui.textarea(
                "Environment",
                placeholder="Enter environmental variables for used algorithms.",
            ).classes("w-full")
            if inspection_profile is not None:
                profile_environment.set_value(inspection_profile.environment)

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save" if inspection_profile is None else "Update",
                    on_click=_handle_push_profile,
                    color="positive",
                )

        ui.markdown("##### **Registered profiles**")
        profile_list_container = ui.list().classes("w-full").props("dense")
        _inject_profile_list()

    return view
