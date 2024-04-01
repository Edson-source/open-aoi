
        # with ui.column():
        #     # TODO: provide image navigation
        #     with ui.interactive_image(im) as ii:
        #         ui.button("Take image").classes("absolute bottom-0 right-0 m-2")

        #     template_title = ui.input(
        #         label="Template title",
        #         placeholder=f"Enter any value... [{TITLE_LIMIT}]",
        #         on_change=lambda e: template_title_display.set_text(
        #             f"[{len(template_title.value.strip())}/{TITLE_LIMIT}] {template_title.value.strip()}"
        #         ),
        #         validation={
        #             "Title is too long": lambda value: len(value.strip())
        #             <= TITLE_LIMIT,
        #             "Title is too short": lambda value: len(value.strip()) != 0,
        #         },
        #     ).classes("w-full")
        #     template_title_display = ui.label("").classes("text-secondary")

        #     with ui.row().classes("w-full"):
        #         ui.space()
        #         ui.button(
        #             "Save as template",
        #             on_click=lambda: 1,
        #         )
