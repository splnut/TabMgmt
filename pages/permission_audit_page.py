import os
import pandas as pd
import customtkinter as ctk
from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, FormRow, SearchableMultiSelect

class PermissionAuditPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.projects = []
        self.latest_results = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        SectionHeader(
            self,
            "Permission Audit",
            "Audit Tableau project, workbook, and published data source permissions"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.scroll_area.grid_columnconfigure(0, weight=1)

        # Scope card
        scope_card = Card(self.scroll_area)
        scope_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        scope_card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(scope_card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(18, 8))
        ctk.CTkButton(top, text="Load Projects", command=self.load_projects).pack(side="left")

        self.scope_menu = ctk.CTkOptionMenu(
            top,
            values=["Entire Site", "Selected Projects"]
        )
        self.scope_menu.pack(side="right")
        self.scope_menu.set("Selected Projects")

        self.project_box = SearchableMultiSelect(scope_card, title="Projects", height=220)
        self.project_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        # Content scope card
        content_card = Card(self.scroll_area)
        content_card.grid(row=1, column=0, sticky="ew", pady=12)

        content_inner = ctk.CTkFrame(content_card, fg_color="transparent")
        content_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(content_inner, text="Include Content Types", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.include_projects_var = ctk.BooleanVar(value=True)
        self.include_workbooks_var = ctk.BooleanVar(value=True)
        self.include_datasources_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(content_inner, text="Projects", variable=self.include_projects_var).grid(row=1, column=0, sticky="w", padx=(0, 20))
        ctk.CTkCheckBox(content_inner, text="Workbooks", variable=self.include_workbooks_var).grid(row=1, column=1, sticky="w", padx=(0, 20))
        ctk.CTkCheckBox(content_inner, text="Published Data Sources", variable=self.include_datasources_var).grid(row=1, column=2, sticky="w")

        # Rules card
        rules_card = Card(self.scroll_area)
        rules_card.grid(row=2, column=0, sticky="ew", pady=12)

        rules_inner = ctk.CTkFrame(rules_card, fg_color="transparent")
        rules_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(rules_inner, text="Audit Rules", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self.rule_all_users = ctk.BooleanVar(value=True)
        self.rule_direct_user = ctk.BooleanVar(value=True)
        self.rule_non_inherited_wb = ctk.BooleanVar(value=True)
        self.rule_non_inherited_ds = ctk.BooleanVar(value=True)
        self.rule_high_priv = ctk.BooleanVar(value=True)
        self.rule_change_permissions = ctk.BooleanVar(value=True)
        self.rule_project_leader = ctk.BooleanVar(value=True)

        rule_checks = [
            ("Flag All Users access", self.rule_all_users),
            ("Flag direct user permissions", self.rule_direct_user),
            ("Flag non-inherited workbook permissions", self.rule_non_inherited_wb),
            ("Flag non-inherited datasource permissions", self.rule_non_inherited_ds),
            ("Flag high-privilege capabilities", self.rule_high_priv),
            ("Flag Change Permissions grants", self.rule_change_permissions),
            ("Flag Project Leader-like grants", self.rule_project_leader),
        ]

        for idx, (label, var) in enumerate(rule_checks, start=1):
            r, c = divmod(idx - 1, 2)
            ctk.CTkCheckBox(rules_inner, text=label, variable=var).grid(row=r + 1, column=c, sticky="w", padx=(0, 20), pady=6)

        # Baseline card
        baseline_card = Card(self.scroll_area)
        baseline_card.grid(row=3, column=0, sticky="ew", pady=12)
        baseline_card.grid_columnconfigure(0, weight=1)

        baseline_inner = ctk.CTkFrame(baseline_card, fg_color="transparent")
        baseline_inner.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(baseline_inner, text="Standards / Baseline", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        broad_row = FormRow(baseline_inner, "Broad Groups (comma-separated)")
        broad_row.grid(row=1, column=0, sticky="ew", pady=6)
        self.broad_groups_entry = broad_row.entry
        self.broad_groups_entry.insert(0, "All Users")

        forbidden_row = FormRow(baseline_inner, "Forbidden Groups (comma-separated)")
        forbidden_row.grid(row=2, column=0, sticky="ew", pady=6)
        self.forbidden_groups_entry = forbidden_row.entry
        self.forbidden_groups_entry.insert(0, "All Users")

        approved_row = FormRow(baseline_inner, "Approved High-Privilege Groups (comma-separated)")
        approved_row.grid(row=3, column=0, sticky="ew", pady=6)
        self.approved_groups_entry = approved_row.entry
        self.approved_groups_entry.insert(0, "All - Tableau Site - Admin,All - Tableau Site - Publisher")
        

        self.compare_to_baseline_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            baseline_inner,
            text="Compare findings to baseline config",
            variable=self.compare_to_baseline_var
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))

        # Action card
        action_card = Card(self.scroll_area)
        action_card.grid(row=4, column=0, sticky="ew", pady=12)

        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkButton(action_inner, text="Preview Summary", command=self.preview_summary).pack(side="left", padx=(0, 12))
        ctk.CTkButton(action_inner, text="Export Full Audit", command=self.export_full_audit).pack(side="left", padx=(0, 12))
        ctk.CTkButton(action_inner, text="Export Exceptions Only", command=self.export_exceptions_only).pack(side="left")

        # Results card
        results_card = Card(self.scroll_area)
        results_card.grid(row=5, column=0, sticky="ew", pady=(12, 24))
        results_card.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(results_card, text="Results", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(18, 8)
        )

        self.results_label = ctk.CTkLabel(
            results_card,
            text="Run a preview or export to see permission audit results.",
            anchor="w",
            justify="left",
            wraplength=1100
        )
        self.results_label.grid(row=1, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 18))

    def load_projects(self):
        def task():
            return [p.name for p in self.app.tableau.get_projects()]

        def success(projects):
            self.projects = sorted(projects, key=lambda x: x.lower())
            self.project_box.set_items(self.projects)
            self.set_status(f"Loaded {len(self.projects)} projects.")

        self.run_async(task, on_success=success, status_text="Loading projects...")

    def _selected_projects(self):
        if self.scope_menu.get() == "Entire Site":
            return None
        selected = self.project_box.get_selected()
        if not selected:
            raise RuntimeError("Select at least one project or switch scope to Entire Site.")
        return selected

    def _audit_options(self):
        return {
            "project_names": self._selected_projects(),
            "include_projects": self.include_projects_var.get(),
            "include_workbooks": self.include_workbooks_var.get(),
            "include_datasources": self.include_datasources_var.get(),
            "flag_all_users": self.rule_all_users.get(),
            "flag_direct_user": self.rule_direct_user.get(),
            "flag_non_inherited_workbooks": self.rule_non_inherited_wb.get(),
            "flag_non_inherited_datasources": self.rule_non_inherited_ds.get(),
            "flag_high_privilege": self.rule_high_priv.get(),
            "flag_change_permissions": self.rule_change_permissions.get(),
            "flag_project_leader": self.rule_project_leader.get(),
            "broad_groups": [x.strip() for x in self.broad_groups_entry.get().split(",") if x.strip()],
            "forbidden_groups": [x.strip() for x in self.forbidden_groups_entry.get().split(",") if x.strip()],
            "approved_high_priv_groups": [x.strip() for x in self.approved_groups_entry.get().split(",") if x.strip()],
            "compare_to_baseline": self.compare_to_baseline_var.get(),
        }

    def preview_summary(self):
        def task(progress=None):
            return self.app.tableau.get_permission_audit_summary(**self._audit_options())

        def success(summary):
            self.latest_results = summary
            self.results_label.configure(
                text=(
                    f"Projects Audited: {summary['projects_audited']}\n"
                    f"Workbooks Audited: {summary['workbooks_audited']}\n"
                    f"Data Sources Audited: {summary['datasources_audited']}\n"
                    f"High Findings: {summary['high_findings']}\n"
                    f"Medium Findings: {summary['medium_findings']}\n"
                    f"Low Findings: {summary['low_findings']}\n"
                    f"Total Findings: {summary['total_findings']}"
                )
            )
            self.set_status("Permission audit preview complete.")

        self.run_async(task, on_success=success, status_text="Auditing permissions...")

    def export_full_audit(self):
        def task(progress=None):
            reports = self.app.tableau.generate_permission_audit_report(**self._audit_options())
            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
            path = os.path.join(documents, 'Tableau Server - Permission Audit Report.xlsx')

            with pd.ExcelWriter(path) as writer:
                for sheet_name, df in reports.items():
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            return path

        def success(path):
            self.results_label.configure(text=f"Saved full permission audit to:\n{path}")
            self.set_status("Permission audit report saved.")

        self.run_async(task, on_success=success, status_text="Generating permission audit report...")

    def export_exceptions_only(self):
        def task(progress=None):
            reports = self.app.tableau.generate_permission_audit_report(**self._audit_options())
            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
            path = os.path.join(documents, 'Tableau Server - Permission Audit Exceptions.xlsx')

            exceptions_df = reports.get("Exceptions", pd.DataFrame())
            with pd.ExcelWriter(path) as writer:
                exceptions_df.to_excel(writer, sheet_name="Exceptions", index=False)

            return path

        def success(path):
            self.results_label.configure(text=f"Saved permission exceptions report to:\n{path}")
            self.set_status("Permission exceptions report saved.")

        self.run_async(task, on_success=success, status_text="Generating exceptions report...")