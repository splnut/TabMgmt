import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, CollapsibleCard, FormRow, SearchableMultiSelect


class ConnectionManagementPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.projects = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        SectionHeader(
            self,
            "Connection Management",
            "Manage workbook and published data source connections"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.scroll_area.grid_columnconfigure(0, weight=1)

        project_card = Card(self.scroll_area)
        project_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        project_card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(project_card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(18, 8))
        ctk.CTkButton(top, text="Load Projects", command=self.load_projects).pack(side="left")

        self.project_box = SearchableMultiSelect(project_card, title="Projects", height=220)
        self.project_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.scope_card = Card(self.scroll_area)
        self.scope_card.grid(row=1, column=0, sticky="ew", pady=12)

        scope_inner = ctk.CTkFrame(self.scope_card, fg_color="transparent")
        scope_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(scope_inner, text="Target Scope", width=180, anchor="w").pack(side="left")
        self.scope_menu = ctk.CTkOptionMenu(
            scope_inner,
            values=["Both", "Workbooks Only", "Published Data Sources Only"]
        )
        self.scope_menu.pack(side="right")
        self.scope_menu.set("Both")

        server_card = CollapsibleCard(self.scroll_area, "Server Name", expanded=False)
        server_card.grid(row=2, column=0, sticky="ew", pady=12)

        server_form = ctk.CTkFrame(server_card.body, fg_color="transparent")
        server_form.grid(row=0, column=0, sticky="ew")
        server_form.grid_columnconfigure(0, weight=1)

        old_server_row = FormRow(server_form, "Old Server (* for all)")
        old_server_row.grid(row=0, column=0, sticky="ew", pady=8)
        self.old_server_entry = old_server_row.entry

        new_server_row = FormRow(server_form, "New Server")
        new_server_row.grid(row=1, column=0, sticky="ew", pady=8)
        self.new_server_entry = new_server_row.entry

        btn_row = ctk.CTkFrame(server_form, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row,
            text="Update Server Name",
            command=self.update_server_names
        ).grid(row=0, column=1, sticky="e")

        cred_card = CollapsibleCard(self.scroll_area, "Login Details", expanded=True)
        cred_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        cred_form = ctk.CTkFrame(cred_card.body, fg_color="transparent")
        cred_form.grid(row=0, column=0, sticky="ew")
        cred_form.grid_columnconfigure(0, weight=1)

        server_match_row = FormRow(cred_form, "Server Name to Update Details")
        server_match_row.grid(row=0, column=0, sticky="ew", pady=8)
        self.server_match_entry = server_match_row.entry

        current_user_row = FormRow(cred_form, "Current SQL Username")
        current_user_row.grid(row=1, column=0, sticky="ew", pady=8)
        self.current_username_entry = current_user_row.entry

        new_user_row = FormRow(cred_form, "New SQL Username")
        new_user_row.grid(row=2, column=0, sticky="ew", pady=8)
        self.new_username_entry = new_user_row.entry

        password_row = FormRow(cred_form, "SQL Password", show="*")
        password_row.grid(row=3, column=0, sticky="ew", pady=8)
        self.password_entry = password_row.entry

        btn_row2 = ctk.CTkFrame(cred_form, fg_color="transparent")
        btn_row2.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        btn_row2.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row2,
            text="Update Login Details",
            command=self.update_credentials
        ).grid(row=0, column=1, sticky="e")

    def load_projects(self):
        def task():
            return [p.name for p in self.app.tableau.get_projects()]

        def success(projects):
            self.projects = projects
            self.project_box.set_items(projects)
            self.set_status(f"Loaded {len(projects)} projects.")

        self.run_async(task, on_success=success, status_text="Loading projects...")

    def _scope_params(self):
        scope = self.scope_menu.get()
        return {
            "include_workbooks": scope in ("Both", "Workbooks Only"),
            "include_datasources": scope in ("Both", "Published Data Sources Only"),
        }

    def update_server_names(self):
        selected_projects = self.project_box.get_selected()
        old_server = self.old_server_entry.get().strip()
        new_server = self.new_server_entry.get().strip()

        if not selected_projects:
            return self.app.show_error("At least one project must be selected.")
        if not old_server:
            return self.app.show_error("Old Server name cannot be empty.")
        if not new_server:
            return self.app.show_error("New Server name cannot be empty.")

        if not self.confirm(
            "Confirm Server Update",
            f"Update server name across selected projects?\n\nProjects: {len(selected_projects)}\nOld server: {old_server}\nNew server: {new_server}"
        ):
            return

        scope_params = self._scope_params()

        def task():
            return self.app.tableau.update_connection_server_names(
                project_names=selected_projects,
                old_server=old_server,
                new_server=new_server,
                **scope_params
            )

        def success(results):
            self.app.show_info(
                f"Server names updated successfully.\n\n"
                f"Workbooks updated: {len(results['workbooks_updated'])}\n"
                f"Published data sources updated: {len(results['datasources_updated'])}"
            )

        self.run_async(task, on_success=success, status_text="Updating server names...")

    def update_credentials(self):
        selected_projects = self.project_box.get_selected()
        server_match = self.server_match_entry.get().strip()
        current_username = self.current_username_entry.get().strip()
        new_username = self.new_username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not selected_projects:
            return self.app.show_error("At least one project must be selected.")
        if not server_match:
            return self.app.show_error("Server name cannot be empty.")
        if not current_username:
            return self.app.show_error("Current Username cannot be empty.")
        if not password and not new_username:
            return self.app.show_error("Either New Username or Password must be provided.")

        if not self.confirm(
            "Confirm Credential Update",
            f"Update connection credentials across selected projects?\n\nProjects: {len(selected_projects)}\nServer match: {server_match}\nCurrent username: {current_username}"
        ):
            return

        scope_params = self._scope_params()

        def task():
            return self.app.tableau.update_connection_credentials(
                project_names=selected_projects,
                server_match=server_match,
                current_username=current_username,
                new_username=new_username or None,
                password=password or None,
                **scope_params
            )

        def success(results):
            self.app.show_info(
                f"Login details updated successfully.\n\n"
                f"Workbooks updated: {len(results['workbooks_updated'])}\n"
                f"Published data sources updated: {len(results['datasources_updated'])}"
            )

        self.run_async(task, on_success=success, status_text="Updating connection credentials...")