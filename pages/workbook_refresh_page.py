import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, SearchableMultiSelect


class WorkbookRefreshPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.grouped = {}
        self.projects = []

        self.grid_columnconfigure((0, 1), weight=1)

        SectionHeader(self, "Workbook Refresh", "Select projects and optionally specific workbooks").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12)
        )

        controls = Card(self)
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=12)

        inner = ctk.CTkFrame(controls, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkButton(inner, text="Load Projects & Workbooks", command=self.load_data).pack(side="left")

        self.projects_box = SearchableMultiSelect(self, title="Projects", height=360)
        self.projects_box.grid(row=2, column=0, sticky="nsew", padx=(24, 12), pady=12)

        self.workbooks_box = SearchableMultiSelect(self, title="Workbooks", height=360)
        self.workbooks_box.grid(row=2, column=1, sticky="nsew", padx=(12, 24), pady=12)

        action_card = Card(self)
        action_card.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 24))
        btn_frame = ctk.CTkFrame(action_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=18, pady=18)

        ctk.CTkButton(btn_frame, text="Sync Workbook List From Selected Projects", command=self.sync_workbooks).pack(
            side="left"
        )
        ctk.CTkButton(btn_frame, text="Refresh Selected", command=self.refresh_selected).pack(side="right")

    def load_data(self):
        def task():
            return self.app.tableau.get_workbooks_grouped_by_project()

        def success(grouped):
            self.grouped = grouped
            self.projects = sorted(grouped.keys())
            self.projects_box.set_items(self.projects)
            self.workbooks_box.set_items([])
            self.set_status(f"Loaded {len(self.projects)} projects and workbook list.")

        self.run_async(task, on_success=success, status_text="Loading workbooks...")

    def sync_workbooks(self):
        selected_projects = self.projects_box.get_selected()
        workbook_names = []

        for project in selected_projects:
            workbook_names.extend([wb.name for wb in self.grouped.get(project, [])])

        deduped = sorted(set(workbook_names), key=lambda x: x.lower())
        self.workbooks_box.set_items(deduped)

    def refresh_selected(self):
        selected_projects = self.projects_box.get_selected() or self.projects
        selected_workbooks = self.workbooks_box.get_selected()

        if not selected_projects:
            return self.app.show_error("Load and select at least one project.")

        if not self.confirm(
            "Confirm Refresh",
            f"Trigger refresh for selected content?\n\nProjects: {len(selected_projects)}\nWorkbooks filter: {len(selected_workbooks)}"
        ):
            return

        def task():
            return self.app.tableau.refresh_workbooks(
                project_names=selected_projects,
                workbook_names=selected_workbooks
            )

        def success(result):
            self.app.show_info(f"Triggered refresh for {len(result)} workbooks.")

        self.run_async(task, on_success=success, status_text="Refreshing workbooks...")