import os
import pandas as pd
import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, FormRow, SearchableMultiSelect

class ToolsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.projects = []
        self.workbooks_by_project = {}

        self.preview_rows = []
        self.preview_export_path = ""
        self.preview_signature = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll_area.grid_columnconfigure((0, 1), weight=1)

        SectionHeader(
            self.scroll_area,
            "Tools",
            "Administrative utilities with room for future expansion"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12))

        selector_card = Card(self.scroll_area)
        selector_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))
        selector_card.grid_columnconfigure(0, weight=1)

        selector_inner = ctk.CTkFrame(selector_card, fg_color="transparent")
        selector_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(
            selector_inner,
            text="Select Tool",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        self.tool_menu = ctk.CTkOptionMenu(
            selector_inner,
            values=[
                "Remove All Users Group Permission",
                "Remove Termed Users",
                "Update Permission Data",
            ],
            command=lambda _=None: self.on_tool_change()
        )
        self.tool_menu.pack(anchor="w")
        self.tool_menu.set("Remove All Users Group Permission")

        self.content_frame = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.content_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=24, pady=(0, 24))
        self.content_frame.grid_columnconfigure((0, 1), weight=1)

        self.remove_all_users_card = None
        self.remove_termed_card = None
        self.update_permission_data_card = None

        self._build_remove_all_users_tool()
        self._build_placeholder_tools()
        self.on_tool_change()
        
        self.preview_rows = []
        self.preview_export_path = ""
        self.preview_signature = None

    def _build_remove_all_users_tool(self):
        self.remove_all_users_card = Card(self.content_frame)
        self.remove_all_users_card.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.remove_all_users_card.grid_columnconfigure((0, 1), weight=1)
        self.remove_all_users_card.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            self.remove_all_users_card,
            text="Remove All Users Group Permission",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            self.remove_all_users_card,
            text=(
                "Preview and remove group permissions from Tableau projects and workbooks "
                "with exclusions."
            ),
            justify="left",
            wraplength=900
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

        button_row = ctk.CTkFrame(self.remove_all_users_card, fg_color="transparent")
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        button_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            button_row,
            text="Load Projects and Workbooks",
            command=self.load_projects_and_workbooks
        ).grid(row=0, column=0, sticky="w")

        form_frame = ctk.CTkFrame(self.remove_all_users_card, fg_color="transparent")
        form_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 12))
        form_frame.grid_columnconfigure((0, 1), weight=1)
        form_frame.grid_rowconfigure(1, weight=1)

        left_col = ctk.CTkFrame(form_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_col.grid_columnconfigure(0, weight=1)
        left_col.grid_rowconfigure(1, weight=1)

        group_row = FormRow(left_col, "User Group to Remove")
        group_row.grid(row=0, column=0, sticky="ew", pady=8)
        self.group_to_remove_entry = group_row.entry
        self.group_to_remove_entry.insert(0, "All Users")

        self.ignore_projects_box = SearchableMultiSelect(
            left_col,
            title="Projects to Ignore",
            height=280
        )
        self.ignore_projects_box.grid(row=1, column=0, sticky="nsew", pady=8)

        right_col = ctk.CTkFrame(form_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(0, weight=1)

        self.ignore_workbooks_box = SearchableMultiSelect(
            right_col,
            title="Workbooks to Ignore",
            height=280
        )
        self.ignore_workbooks_box.grid(row=0, column=0, sticky="nsew", pady=8)

        self.ignore_workbooks_box.set_items(["User Dashboard"])
        for item, var in self.ignore_workbooks_box.vars.items():
            if item == "User Dashboard":
                var.set(True)

        preview_card = Card(self.remove_all_users_card)
        preview_card.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 12))
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            preview_card,
            text="Preview",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.preview_summary_label = ctk.CTkLabel(
            preview_card,
            text="No preview generated yet.",
            anchor="w",
            justify="left",
            wraplength=1000
        )
        self.preview_summary_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.preview_text = ctk.CTkTextbox(preview_card, height=260, wrap="none")
        self.preview_text.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.preview_text.insert("1.0", "Preview results will appear here.")
        self.preview_text.configure(state="disabled")

        safety_frame = ctk.CTkFrame(self.remove_all_users_card, fg_color="transparent")
        safety_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        safety_frame.grid_columnconfigure(0, weight=1)

        self.confirm_var = ctk.BooleanVar(value=False)
        self.confirm_checkbox = ctk.CTkCheckBox(
            safety_frame,
            text="I understand this will remove permissions and cannot be undone automatically.",
            variable=self.confirm_var,
            command=self._update_run_button_state
        )
        self.confirm_checkbox.grid(row=0, column=0, sticky="w")

        action_row = ctk.CTkFrame(self.remove_all_users_card, fg_color="transparent")
        action_row.grid(row=6, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 18))
        action_row.grid_columnconfigure(0, weight=1)

        self.preview_button = ctk.CTkButton(
            action_row,
            text="Preview Changes",
            command=self.preview_remove_all_users_group_permission
        )
        self.preview_button.grid(row=0, column=0, sticky="w")

        self.run_button = ctk.CTkButton(
            action_row,
            text="Apply Changes",
            command=self.run_remove_all_users_group_permission,
            state="disabled"
        )
        self.run_button.grid(row=0, column=1, sticky="e")

    def _build_placeholder_tools(self):
        self._build_remove_termed_users_tool()

        self.update_permission_data_card = Card(self.content_frame)
        self.update_permission_data_card.grid(row=0, column=0, columnspan=2, sticky="nsew")
        ctk.CTkLabel(
            self.update_permission_data_card,
            text="Update Permission Data",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            self.update_permission_data_card,
            text="This tool is reserved for future implementation.",
            justify="left"
        ).pack(anchor="w", padx=18, pady=(0, 18))

    def on_tool_change(self):
        selected = self.tool_menu.get()

        self.remove_all_users_card.grid_remove()
        self.remove_termed_card.grid_remove()
        self.update_permission_data_card.grid_remove()

        if selected == "Remove All Users Group Permission":
            self.remove_all_users_card.grid()
        elif selected == "Remove Termed Users":
            self.remove_termed_card.grid()
        elif selected == "Update Permission Data":
            self.update_permission_data_card.grid()

    def load_projects_and_workbooks(self):
        def task(progress=None):
            if progress:
                progress("Loading projects and workbooks...")
            grouped = self.app.tableau.get_workbooks_grouped_by_project()
            return grouped

        def success(grouped):
            self.workbooks_by_project = grouped or {}
            self.projects = sorted(self.workbooks_by_project.keys(), key=lambda x: x.lower())

            self.ignore_projects_box.set_items(self.projects)

            workbook_names = []
            for project_name, workbooks in self.workbooks_by_project.items():
                for wb in workbooks:
                    workbook_names.append(wb.name)

            workbook_names = sorted(set(workbook_names), key=lambda x: x.lower())

            if "User Dashboard" not in workbook_names:
                workbook_names.insert(0, "User Dashboard")

            self.ignore_workbooks_box.set_items(workbook_names)

            for item, var in self.ignore_workbooks_box.vars.items():
                if item == "User Dashboard":
                    var.set(True)

            self.set_status(f"Loaded {len(self.projects)} projects and {len(workbook_names)} workbooks.")

        self.run_async(
            task,
            on_success=success,
            status_text="Loading projects and workbooks..."
        )

    def run_remove_all_users_group_permission(self):
        group_name = self.group_to_remove_entry.get().strip() or "All Users"
        ignore_projects = self.ignore_projects_box.get_selected()
        ignore_workbooks = self.ignore_workbooks_box.get_selected()

        if not self.confirm_var.get():
            return self.app.show_error("You must check the confirmation box before applying changes.")

        current_signature = self._current_preview_signature()
        if current_signature != self.preview_signature:
            return self.app.show_error(
                "The form changed since the last preview. Please run Preview Changes again before applying."
            )

        if not self.preview_rows:
            return self.app.show_error("No preview results available to apply.")

        if not self.confirm(
            "Confirm Permission Removal",
            f"Apply {len(self.preview_rows)} permission removals for group '{group_name}'?"
        ):
            return

        def task(progress=None):
            return self.app.tableau.apply_remove_group_permissions_from_content(
                preview_rows=self.preview_rows,
                group_name=group_name,
                progress_callback=progress
            )

        def success(result):
            changes = result.get("changes", [])
            export_path = result.get("export_path", "")

            self.preview_summary_label.configure(
                text=(
                    f"Changes applied successfully.\n"
                    f"Changes made: {len(changes)}\n"
                    f"Exported file: {export_path or 'No file created'}"
                )
            )
            self._set_preview_text(self._format_preview_rows(changes))
            self.app.show_info(
                f"Permission removal complete.\n\n"
                f"Changes made: {len(changes)}\n"
                f"Exported file: {export_path or 'No file created'}"
            )
            self.set_status("Permission removal completed.")

        self.run_async(
            task,
            on_success=success,
            status_text="Applying permission removals..."
        )
        
    def _update_run_button_state(self):
        if self.confirm_var.get():
            self.run_button.configure(state="normal")
        else:
            self.run_button.configure(state="disabled")


    def _current_preview_signature(self):
        return (
            (self.group_to_remove_entry.get().strip() or "All Users").lower(),
            tuple(sorted(self.ignore_projects_box.get_selected())),
            tuple(sorted(self.ignore_workbooks_box.get_selected())),
        )


    def _set_preview_text(self, text):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)
        self.preview_text.configure(state="disabled")


    def _format_preview_rows(self, rows, max_lines=250):
        if not rows:
            return "No matching permissions were found to remove."

        lines = []
        for i, row in enumerate(rows[:max_lines], start=1):
            lines.append(
                f"{i}. Type: {row.get('content_type', '')} | "
                f"Project: {row.get('project_name', '')} | "
                f"Content: {row.get('content_name', '')} | "
                f"Group: {row.get('group_name', '')} | "
                f"Capability: {row.get('capability_name', '')} | "
                f"Mode: {row.get('mode', '')}"
            )

        if len(rows) > max_lines:
            lines.append("")
            lines.append(f"...and {len(rows) - max_lines} more rows not shown.")

        return "\n".join(lines)
        
    def preview_remove_all_users_group_permission(self):
        group_name = self.group_to_remove_entry.get().strip() or "All Users"
        ignore_projects = self.ignore_projects_box.get_selected()
        ignore_workbooks = self.ignore_workbooks_box.get_selected()

        def task(progress=None):
            return self.app.tableau.preview_remove_group_permissions_from_content(
                group_name=group_name,
                ignore_projects=ignore_projects,
                ignore_workbooks=ignore_workbooks,
                progress_callback=progress
            )

        def success(result):
            self.preview_rows = result.get("changes", [])
            self.preview_export_path = result.get("export_path", "")
            self.preview_signature = self._current_preview_signature()

            self.preview_summary_label.configure(
                text=(
                    f"Preview complete.\n"
                    f"Potential changes: {len(self.preview_rows)}\n"
                    f"Preview export: {self.preview_export_path or 'Not created'}"
                )
            )
            self._set_preview_text(self._format_preview_rows(self.preview_rows))
            self.set_status(f"Preview loaded: {len(self.preview_rows)} potential changes found.")

        self.run_async(
            task,
            on_success=success,
            status_text="Previewing permission removals..."
        )
        
    def _build_remove_termed_users_tool(self):
        self.remove_termed_card = Card(self.content_frame)
        self.remove_termed_card.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.remove_termed_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.remove_termed_card,
            text="Remove Termed Users",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            self.remove_termed_card,
            text=(
                "Preview and remove Tableau users whose NTLOGIN appears in the recent-term list "
                "returned from SQL Server."
            ),
            justify="left",
            wraplength=900
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

        form_frame = ctk.CTkFrame(self.remove_termed_card, fg_color="transparent")
        form_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        form_frame.grid_columnconfigure((0, 1), weight=1)

        left_col = ctk.CTkFrame(form_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left_col.grid_columnconfigure(0, weight=1)

        right_col = ctk.CTkFrame(form_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right_col.grid_columnconfigure(0, weight=1)

        sql_server_row = FormRow(left_col, "SQL Server")
        sql_server_row.grid(row=0, column=0, sticky="ew", pady=8)
        self.sql_server_entry = sql_server_row.entry
        self.sql_server_entry.insert(0, "YOUR_SQL_SERVER")

        sql_database_row = FormRow(left_col, "SQL Database")
        sql_database_row.grid(row=1, column=0, sticky="ew", pady=8)
        self.sql_database_entry = sql_database_row.entry
        self.sql_database_entry.insert(0, "master")

        sql_driver_row = FormRow(left_col, "SQL Driver")
        sql_driver_row.grid(row=2, column=0, sticky="ew", pady=8)
        self.sql_driver_entry = sql_driver_row.entry
        self.sql_driver_entry.insert(0, "ODBC Driver 17 for SQL Server")

        lookback_row = FormRow(left_col, "Lookback Days")
        lookback_row.grid(row=3, column=0, sticky="ew", pady=8)
        self.lookback_days_entry = lookback_row.entry
        self.lookback_days_entry.insert(0, "30")

        sql_username_row = FormRow(right_col, "SQL Username")
        sql_username_row.grid(row=0, column=0, sticky="ew", pady=8)
        self.sql_username_entry = sql_username_row.entry

        sql_password_row = FormRow(right_col, "SQL Password", show="*")
        sql_password_row.grid(row=1, column=0, sticky="ew", pady=8)
        self.sql_password_entry = sql_password_row.entry

        self.exclude_server_roles_var = ctk.BooleanVar(value=True)
        self.exclude_server_roles_checkbox = ctk.CTkCheckBox(
            right_col,
            text="Exclude Tableau users whose site role contains 'Server'",
            variable=self.exclude_server_roles_var
        )
        self.exclude_server_roles_checkbox.grid(row=2, column=0, sticky="w", pady=(12, 8))

        preview_card = Card(self.remove_termed_card)
        preview_card.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 12))
        preview_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            preview_card,
            text="Preview",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.termed_preview_summary_label = ctk.CTkLabel(
            preview_card,
            text="No preview generated yet.",
            anchor="w",
            justify="left",
            wraplength=1000
        )
        self.termed_preview_summary_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.termed_preview_text = ctk.CTkTextbox(preview_card, height=260, wrap="none")
        self.termed_preview_text.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.termed_preview_text.insert("1.0", "Preview results will appear here.")
        self.termed_preview_text.configure(state="disabled")

        safety_frame = ctk.CTkFrame(self.remove_termed_card, fg_color="transparent")
        safety_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        safety_frame.grid_columnconfigure(0, weight=1)

        self.termed_confirm_var = ctk.BooleanVar(value=False)
        self.termed_confirm_checkbox = ctk.CTkCheckBox(
            safety_frame,
            text="I understand this will remove users from Tableau and cannot be undone automatically.",
            variable=self.termed_confirm_var,
            command=self._update_termed_run_button_state
        )
        self.termed_confirm_checkbox.grid(row=0, column=0, sticky="w")

        action_row = ctk.CTkFrame(self.remove_termed_card, fg_color="transparent")
        action_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 18))
        action_row.grid_columnconfigure(0, weight=1)

        self.termed_preview_button = ctk.CTkButton(
            action_row,
            text="Preview Changes",
            command=self.preview_remove_termed_users
        )
        self.termed_preview_button.grid(row=0, column=0, sticky="w")

        self.termed_run_button = ctk.CTkButton(
            action_row,
            text="Apply Changes",
            command=self.run_remove_termed_users,
            state="disabled"
        )
        self.termed_run_button.grid(row=0, column=1, sticky="e")
        
    def _update_termed_run_button_state(self):
        self.termed_run_button.configure(
            state="normal" if self.termed_confirm_var.get() else "disabled"
        )

    def _current_termed_preview_signature(self):
        return (
            self.sql_server_entry.get().strip(),
            self.sql_database_entry.get().strip(),
            self.sql_driver_entry.get().strip(),
            self.sql_username_entry.get().strip(),
            self.lookback_days_entry.get().strip(),
            bool(self.exclude_server_roles_var.get()),
        )

    def _set_termed_preview_text(self, text):
        self.termed_preview_text.configure(state="normal")
        self.termed_preview_text.delete("1.0", "end")
        self.termed_preview_text.insert("1.0", text)
        self.termed_preview_text.configure(state="disabled")

    def _format_termed_preview_rows(self, rows, max_lines=250):
        if not rows:
            return "No matching termed Tableau users were found."

        lines = []
        for i, row in enumerate(rows[:max_lines], start=1):
            lines.append(
                f"{i}. NTLOGIN: {row.get('ntlogin', '')} | "
                f"Tableau User ID: {row.get('tableau_user_id', '')} | "
                f"Site Role: {row.get('site_role', '')} | "
                f"Action: {row.get('action', '')} | "
                f"Status: {row.get('status', '')}"
            )

        if len(rows) > max_lines:
            lines.append("")
            lines.append(f"...and {len(rows) - max_lines} more rows not shown.")

        return "\n".join(lines)

    def preview_remove_termed_users(self):
        sql_server = self.sql_server_entry.get().strip()
        sql_database = self.sql_database_entry.get().strip() or "master"
        sql_driver = self.sql_driver_entry.get().strip() or "ODBC Driver 17 for SQL Server"
        sql_username = self.sql_username_entry.get().strip()
        sql_password = self.sql_password_entry.get().strip()

        try:
            lookback_days = int(self.lookback_days_entry.get().strip() or "30")
        except ValueError:
            return self.app.show_error("Lookback Days must be a valid integer.")

        if not sql_server:
            return self.app.show_error("SQL Server is required.")
        if not sql_username:
            return self.app.show_error("SQL Username is required.")
        if not sql_password:
            return self.app.show_error("SQL Password is required.")

        def task(progress=None):
            return self.app.tableau.preview_remove_termed_users(
                sql_server=sql_server,
                sql_username=sql_username,
                sql_password=sql_password,
                sql_database=sql_database,
                sql_driver=sql_driver,
                lookback_days=lookback_days,
                exclude_server_roles=self.exclude_server_roles_var.get(),
                progress_callback=progress
            )

        def success(result):
            self.termed_preview_rows = result.get("changes", [])
            self.termed_preview_export_path = result.get("export_path", "")
            self.termed_preview_signature = self._current_termed_preview_signature()

            self.termed_preview_summary_label.configure(
                text=(
                    f"Preview complete.\n"
                    f"Potential removals: {len(self.termed_preview_rows)}\n"
                    f"Preview export: {self.termed_preview_export_path or 'Not created'}"
                )
            )
            self._set_termed_preview_text(self._format_termed_preview_rows(self.termed_preview_rows))
            self.set_status(f"Preview loaded: {len(self.termed_preview_rows)} potential removals found.")

        self.run_async(
            task,
            on_success=success,
            status_text="Previewing termed users..."
        )

    def run_remove_termed_users(self):
        sql_password = self.sql_password_entry.get().strip()
        if not sql_password:
            return self.app.show_error("SQL Password is required.")

        if not self.termed_confirm_var.get():
            return self.app.show_error("You must check the confirmation box before applying changes.")

        current_signature = self._current_termed_preview_signature()
        if current_signature != self.termed_preview_signature:
            return self.app.show_error(
                "The form changed since the last preview. Please run Preview Changes again before applying."
            )

        if not self.termed_preview_rows:
            return self.app.show_error("No preview results available to apply.")

        if not self.confirm(
            "Confirm Remove Termed Users",
            f"Apply removal for {len(self.termed_preview_rows)} Tableau users?"
        ):
            return

        def task(progress=None):
            return self.app.tableau.apply_remove_termed_users(
                preview_rows=self.termed_preview_rows,
                progress_callback=progress
            )

        def success(result):
            changes = result.get("changes", [])
            export_path = result.get("export_path", "")

            self.termed_preview_summary_label.configure(
                text=(
                    f"Changes applied successfully.\n"
                    f"Users removed: {sum(1 for r in changes if r.get('status') == 'success')}\n"
                    f"Exported file: {export_path or 'No file created'}"
                )
            )
            self._set_termed_preview_text(self._format_termed_preview_rows(changes))
            self.app.show_info(
                f"Remove termed users complete.\n\n"
                f"Processed rows: {len(changes)}\n"
                f"Exported file: {export_path or 'No file created'}"
            )
            self.set_status("Remove termed users completed.")

        self.run_async(
            task,
            on_success=success,
            status_text="Removing termed users..."
        )
        
    def _update_termed_run_button_state(self):
        self.termed_run_button.configure(
            state="normal" if self.termed_confirm_var.get() else "disabled"
        )


    def _current_termed_preview_signature(self):
        return (
            self.sql_server_entry.get().strip(),
            self.sql_database_entry.get().strip(),
            self.sql_driver_entry.get().strip(),
            self.sql_username_entry.get().strip(),
            self.lookback_days_entry.get().strip(),
            bool(self.exclude_server_roles_var.get()),
        )


    def _set_termed_preview_text(self, text):
        self.termed_preview_text.configure(state="normal")
        self.termed_preview_text.delete("1.0", "end")
        self.termed_preview_text.insert("1.0", text)
        self.termed_preview_text.configure(state="disabled")


    def _format_termed_preview_rows(self, rows, max_lines=250):
        if not rows:
            return "No matching termed Tableau users were found."

        lines = []
        for i, row in enumerate(rows[:max_lines], start=1):
            lines.append(
                f"{i}. NTLOGIN: {row.get('ntlogin', '')} | "
                f"Tableau User ID: {row.get('tableau_user_id', '')} | "
                f"Site Role: {row.get('site_role', '')} | "
                f"Action: {row.get('action', '')} | "
                f"Status: {row.get('status', '')}"
            )

        if len(rows) > max_lines:
            lines.append("")
            lines.append(f"...and {len(rows) - max_lines} more rows not shown.")

        return "\n".join(lines)
        
def preview_remove_termed_users(self):
    sql_server = self.sql_server_entry.get().strip()
    sql_database = self.sql_database_entry.get().strip() or "master"
    sql_driver = self.sql_driver_entry.get().strip() or "ODBC Driver 17 for SQL Server"
    sql_username = self.sql_username_entry.get().strip()
    sql_password = self.sql_password_entry.get().strip()

    try:
        lookback_days = int(self.lookback_days_entry.get().strip() or "30")
    except ValueError:
        return self.app.show_error("Lookback Days must be a valid integer.")

    if not sql_server:
        return self.app.show_error("SQL Server is required.")
    if not sql_username:
        return self.app.show_error("SQL Username is required.")
    if not sql_password:
        return self.app.show_error("SQL Password is required.")

    def task(progress=None):
        return self.app.tableau.preview_remove_termed_users(
            sql_server=sql_server,
            sql_username=sql_username,
            sql_password=sql_password,
            sql_database=sql_database,
            sql_driver=sql_driver,
            lookback_days=lookback_days,
            exclude_server_roles=self.exclude_server_roles_var.get(),
            progress_callback=progress
        )

    def success(result):
        self.termed_preview_rows = result.get("changes", [])
        self.termed_preview_export_path = result.get("export_path", "")
        self.termed_preview_signature = self._current_termed_preview_signature()

        self.termed_preview_summary_label.configure(
            text=(
                f"Preview complete.\n"
                f"Potential removals: {len(self.termed_preview_rows)}\n"
                f"Preview export: {self.termed_preview_export_path or 'Not created'}"
            )
        )
        self._set_termed_preview_text(self._format_termed_preview_rows(self.termed_preview_rows))
        self.set_status(f"Preview loaded: {len(self.termed_preview_rows)} potential removals found.")

    self.run_async(
        task,
        on_success=success,
        status_text="Previewing termed users..."
    )

    def run_remove_termed_users(self):
        sql_password = self.sql_password_entry.get().strip()
        if not sql_password:
            return self.app.show_error("SQL Password is required.")

        if not self.termed_confirm_var.get():
            return self.app.show_error("You must check the confirmation box before applying changes.")

        current_signature = self._current_termed_preview_signature()
        if current_signature != self.termed_preview_signature:
            return self.app.show_error(
                "The form changed since the last preview. Please run Preview Changes again before applying."
            )

        if not self.termed_preview_rows:
            return self.app.show_error("No preview results available to apply.")

        if not self.confirm(
            "Confirm Remove Termed Users",
            f"Apply removal for {len(self.termed_preview_rows)} Tableau users?"
        ):
            return

        def task(progress=None):
            return self.app.tableau.apply_remove_termed_users(
                preview_rows=self.termed_preview_rows,
                progress_callback=progress
            )

        def success(result):
            changes = result.get("changes", [])
            export_path = result.get("export_path", "")

            self.termed_preview_summary_label.configure(
                text=(
                    f"Changes applied successfully.\n"
                    f"Users removed: {sum(1 for r in changes if r.get('status') == 'success')}\n"
                    f"Exported file: {export_path or 'No file created'}"
                )
            )
            self._set_termed_preview_text(self._format_termed_preview_rows(changes))
            self.app.show_info(
                f"Remove termed users complete.\n\n"
                f"Processed rows: {len(changes)}\n"
                f"Exported file: {export_path or 'No file created'}"
            )
            self.set_status("Remove termed users completed.")

        self.run_async(
            task,
            on_success=success,
            status_text="Removing termed users..."
        )