import logging
from datetime import datetime
from typing import Optional
from functools import partial

from nicegui import app, ui
from fastapi.responses import RedirectResponse

from open_aoi_core.services import StandardClient
from open_aoi_core.controllers.accessor import AccessorController
from open_aoi_core.controllers.inspection import InspectionController
from open_aoi_core.exceptions import AuthenticationException
from open_aoi_portal.settings import (
    ACCESS_PAGE,
    INSPECTION_DETAIL_PAGE,
    HOME_PAGE,
    APP_TITLE,
)
from open_aoi_portal.common import (
    inject_header,
    get_session,
    safe_view,
    safe_operation,
)

logger = logging.getLogger("ui.home")

# How many inspections per page to show
SELECT_AMOUNT = 4  # +1


def get_view(node: StandardClient):
    @safe_view
    async def view(
        select_from_id: Optional[int] = None, select_to_id: Optional[int] = None
    ) -> Optional[RedirectResponse]:
        session = get_session()
        accessor_controller = AccessorController(session)
        inspection_controller = InspectionController(session)

        try:
            accessor = accessor_controller.identify_session_accessor(app.storage.user)
            assert accessor.role.allow_system_view
            assert accessor.role.allow_inspection_view
            assert (select_from_id is not None and select_to_id is not None) or (
                select_from_id is None and select_to_id is None
            )
        except (AssertionError, AuthenticationException):
            accessor_controller.revoke_session_access(app.storage.user)
            return RedirectResponse(ACCESS_PAGE)

        # ------------------------------------
        # Local injections
        @safe_operation
        async def _inject_inspection_list():
            nonlocal select_from_id, select_to_id, do_update
            if select_from_id is None and select_to_id is None:
                try:
                    last_inspection = inspection_controller.retrieve_last()
                    assert last_inspection is not None
                except AssertionError:
                    pass
                else:
                    select_from_id = last_inspection.id
                    select_to_id = select_from_id - SELECT_AMOUNT

            try:
                inspection_list = inspection_controller.list(
                    inspection_controller.Order.desc,
                    select_from_id=select_from_id,
                    select_to_id=select_to_id,
                )
                inspection_list_container.clear()
            except Exception as e:
                logger.exception(e)
                ui.notify("Failed to list recent inspections.", type="negative")
                return

            if len(inspection_list):
                with inspection_list_container:
                    for inspection in inspection_list:
                        url = INSPECTION_DETAIL_PAGE.format(inspection_id=inspection.id)
                        with ui.item().props("clickable"):
                            with ui.item_section():
                                with ui.row():
                                    ui.markdown(
                                        (
                                            f"Inspection {inspection.id} on {inspection.inspection_profile.identification_code} at  {inspection.created_at}. "
                                            f"Overall **{ 'passed' if inspection.overall_passed else 'rejected'}** "
                                        )
                                    )
                                    ui.space()
                                    ui.button(
                                        icon="info",
                                        color="white",
                                        on_click=lambda: ui.navigate.to(url),
                                    ).props("size=sm")
                next_page_container.clear()
                with next_page_container:
                    ui.space()
                    ui.button(
                        icon="navigate_before",
                        color="white",
                        on_click=lambda: ui.navigate.to(
                            f"{HOME_PAGE}?select_from_id={inspection_list[0].id}&select_to_id={inspection_list[0].id + SELECT_AMOUNT}"
                        ),
                    )
                    if (
                        inspection_list[-1].id - 1 > 0
                    ):  # At least one inspection to show
                        ui.button(
                            icon="navigate_next",
                            color="white",
                            on_click=lambda: ui.navigate.to(
                                f"{HOME_PAGE}?select_from_id={inspection_list[-1].id}&select_to_id={inspection_list[-1].id - SELECT_AMOUNT}",
                            ),
                        )
            else:
                with inspection_list_container:
                    with ui.card().classes("w-full bg-primary text-white"):
                        ui.markdown("**No recent inspections to show**")

            if do_update:
                last_update.set_content(f"Last update *{datetime.now():%X}*")

        # ------------------------------------

        await inject_header(accessor)
        ui.markdown("#### **Overview**")
        ui.markdown(
            f"Welcome to **{APP_TITLE}**. You are logged in as {accessor.title}. "
        )

        if accessor.role.allow_system_operations:
            with ui.expansion(caption="Short user manual").classes("w-full"):
                with ui.timeline(side="right"):
                    ui.timeline_entry(
                        (
                            "Templates são imagens douradas do produto que você deseja inspecionar. "
                            "A partir do template, o sistema irá extrair as características do produto e comparar com as imagens capturadas durante a inspeção. "
                            "Crie um template para cada produto que você deseja inspecionar. "),
                        title="Template",
                        subtitle="Step 1.",
                    )
                    ui.timeline_entry(
                        (
                            "Opcionalmente carregue um módulo personalizado para usar na inspeção. "
                            "Modulos personalizados são arquivos python, que serão invocados para realizar a inspeção. "
                            "Se você não tem um módulo personalizado, não se preocupe, o sistema já conta com um módulo de inspeção baseado em template. "
                        ),
                        title="Módulos personalizados (opcional)",
                        subtitle="Step 2.",
                    )
                    ui.timeline_entry(
                        (
                            "(Opcional) Depois de criar o template, clique no botão de editar para criar as chamadas zonas de inspeção. "
                            "Zonas de inspeção são pequenos retângulos na imagem onde o defeito é esperado. "
                            "Selecione o módulo de inspeção para cada zona, de acordo com o tipo de defeito que você deseja identificar. "
                        ),
                        title="Zonas de inspeção",
                        subtitle="Step 3.",
                    )
                    ui.timeline_entry(
                        (
                            "O passo final de preparação é identificar seu produto e atribuir um template de inspeção a ele. "
                            "Isto é feito com perfis de inspeção. Crie um perfil para cada produto e passe o código de barras do produto para identificação. "
                        ),
                        title="Perfil de inspeção",
                        subtitle="Step 4.",
                    )
                    ui.timeline_entry(
                        (
                            "Depois de tudo estar pronto, é hora de testar!"
                            "Vá para a inspeção ao vivo e acione a câmera desejada. "
                            "A imagem será capturada, o produto será identificado e a inspeção será realizada! "
                            "Os gatilhos automáticos de pino são definidos no passo 1. e estão relacionados à câmera."
                        ),
                        title="Test",
                        subtitle="Step 5.",
                        icon="rocket",
                    )

        ui.markdown("##### **Inspeções recentes**")

        last_update = ui.markdown("Sem atualizações.")
        inspection_list_container = ui.list().classes("w-full").props("dense")
        next_page_container = ui.row().classes("w-full")

        do_update = select_from_id is None
        if do_update:
            ui.timer(3.0, _inject_inspection_list)
        await _inject_inspection_list()

    return view
