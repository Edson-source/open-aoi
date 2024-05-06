"""
    This view works with inspection profiles and is used to create, delete and edit them.
"""

import logging
from typing import Optional
from functools import partial

from rclpy.node import Node
from nicegui import ui, app
from fastapi.responses import RedirectResponse

from open_aoi_core.constants import SystemLimit
from open_aoi_core.models import InspectionProfileModel
from open_aoi_core.services import StandardClient
from open_aoi_core.exceptions import AuthenticationException, SystemIntegrityException
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.template import TemplateController
from open_aoi_core.controllers.inspection_profile import InspectionProfileController
from open_aoi_portal.common import (
    ACCESS_PAGE,
    HOME_PAGE,
    INSPECTION_PROFILE_EDIT_PAGE,
    INSPECTION_PROFILE_CREATE_PAGE,
    inject_text_field,
    inject_header,
    get_session,
    confirm,
    safe_view,
)

logger = logging.getLogger("ui.inspection_profile")


def get_view(node: StandardClient):
    @safe_view
    async def view(profile_id: Optional[int] = None) -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        template_controller = TemplateController(session)
        inspection_profile_controller = InspectionProfileController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_system_operations
        except AuthenticationException:
            return RedirectResponse(ACCESS_PAGE)
        except AssertionError:
            return RedirectResponse(HOME_PAGE)

        # -------------------
        # Handlers
        def _handle_create_edit_profile():
            """Function is used to create or edit inspection profile"""
            nonlocal inspection_profile  # For editing profile will be initiated externally
            try:
                assert profile_title.validate()
                assert profile_description.validate()
                assert environment.validate()
                assert identification_code.validate()
                assert template_select.validate()
            except AssertionError:
                ui.notify("Some required parameters are missing", type="warning")
                return

            try:
                template = template_controller.retrieve(template_select.value)
                assert template is not None
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to retrieve data from database.", type="negative")
                return

            title_value = profile_title.value.strip()
            description_value = profile_description.value.strip()
            identification_code_value = identification_code.value.strip()
            environment_value = environment.value.strip()

            if inspection_profile is None:
                try:
                    inspection_profile = inspection_profile_controller.create(
                        title=title_value,
                        description=description_value,
                        identification_code=identification_code_value,
                        environment=environment_value,
                        template=template,
                        accessor=accessor,
                    )
                    inspection_profile_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to create profile.", type="negative")
                    return
                ui.notify("New profile created", type="positive")
            else:
                try:
                    inspection_profile.environment = environment_value
                    inspection_profile_controller.commit()
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to update profile.", type="negative")
                    return
                ui.notify("Updated", type="positive")
            _inject_profile_list()

        def _handle_delete_profile(profile: InspectionProfileModel):
            """Handles delete operation with confirmation"""

            def _delete():
                try:
                    inspection_profile_controller.delete(profile)
                    inspection_profile_controller.commit()
                except SystemIntegrityException as e:
                    logger.exception(e)
                    ui.notify(str(e), type="warning")
                    return
                except Exception as e:
                    logger.exception(e)
                    ui.notify("Failed to delete profile.", type="negative")
                    return

                ui.notify("Profile deleted", type="positive")
                if (
                    inspection_profile is not None
                    and profile.id == inspection_profile.id
                ):
                    ui.open(INSPECTION_PROFILE_CREATE_PAGE)
                    return
                _inject_profile_list()

            confirm(
                f"You are about to delete inspection profile {profile.title} ({profile.identification_code}). Are you sure?",
                _delete,
            )

        def _handle_edit_profile(profile: InspectionProfileModel):
            """Redirect to profile page for editing"""
            ui.open(INSPECTION_PROFILE_EDIT_PAGE.format(profile_id=profile.id))

        def _handle_activate_profile(profile: InspectionProfileModel):
            """Mark profile as active"""
            try:
                inspection_profile_controller.activate(profile)
                inspection_profile_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to push changes to database.", type="negative")
                return
            _inject_profile_list()

        def _handle_deactivate_profile(profile: InspectionProfileModel):
            """Mark profile as inactive"""
            try:
                inspection_profile_controller.deactivate(profile)
                inspection_profile_controller.commit()
            except SystemIntegrityException as e:
                logger.exception(e)
                ui.notify(str(e), type="negative")
                return
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to push changes to database.", type="negative")
                return
            _inject_profile_list()

        # Local injections
        def _inject_profile_list():
            """Generate list of available profiles"""
            profile_list_container.clear()
            profile_list = inspection_profile_controller.list_nested()

            with profile_list_container:
                if len(profile_list):
                    for profile in profile_list:
                        with ui.item(
                            f"{profile.title} ({profile.template.title}, code: {profile.identification_code}). {profile.description}"
                        ).props("clickable"):
                            ui.tooltip(profile.environment or "<<Empty environment>>")
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
                                        color="white",
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
                        ui.markdown("**No profiles to show.**")

        # -------------------

        inject_header(accessor)

        try:
            if profile_id is None:
                inspection_profile = None
            else:
                inspection_profile = inspection_profile_controller.retrieve(profile_id)
            template_list = dict(
                [
                    (template.id, template.title)
                    for template in template_controller.list()
                ]
            )
        except Exception as e:
            logger.exception(e)
            return RedirectResponse(INSPECTION_PROFILE_CREATE_PAGE)

        with ui.column().classes("w-full"):
            ui.markdown("#### **Inspection profile**")
            ui.markdown(
                (
                    "Inspection profile is a way to connect product with template and so with inspection algorithms. "
                    "When product image is captured for test it will be identified with barcode and inspection profile will be looked up (if active). "
                    "After inspection profile is found, template image will be retrieved and inspection conducted according to template's inspection zones. "
                    "If any inspection module require parameters, they should be defined in inspection profile environment field as string in form: PARAMETER=VALUE (one parameter per line)."
                )
            )
            ui.markdown("##### **Create profile**")
            profile_title = inject_text_field(
                "Profile title", "Enter profile title...", SystemLimit.TITLE_LENGTH
            )
            profile_title.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_title.set_value(inspection_profile.title)

            profile_description = inject_text_field(
                "Profile description",
                "Enter profile description...",
                SystemLimit.DESCRIPTION_LENGTH,
            )
            profile_description.set_enabled(inspection_profile is None)
            if inspection_profile is not None:
                profile_description.set_value(inspection_profile.description)

            identification_code = inject_text_field(
                "Product identification code (barcode value)",
                "Enter product code identification...",
                SystemLimit.IDENTIFICATION_CODE_LENGTH,
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

            environment = ui.textarea(
                "Environment",
                placeholder="Enter environmental variables for used algorithms.",
            ).classes("w-full")
            if inspection_profile is not None:
                environment.set_value(inspection_profile.environment)

            with ui.row().classes("w-full"):
                ui.space()
                ui.button(
                    "Save" if inspection_profile is None else "Update",
                    on_click=_handle_create_edit_profile,
                    color="positive",
                )

        ui.markdown("##### **Registered profiles**")
        profile_list_container = ui.list().classes("w-full").props("dense")
        _inject_profile_list()

    return view
