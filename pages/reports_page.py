import os
import pandas as pd
import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader

class ReportsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        SectionHeader(self, "Reports", "Generate and save Tableau reports to your Documents folder").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12)
        )

        self.saved_file_label = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            justify="left",
            wraplength=1100,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1f538d", "#7fb3ff")
        )
        self.saved_file_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))

        card = Card(self)
        card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=24, pady=(12, 24))
        card.grid_columnconfigure((0, 1), weight=1)

        buttons = [
            ("User Report", self.generate_user_report),
            ("User Group Report", self.generate_group_report),
            ("Permission Audit Report", self.generate_permission_audit_report),
            ("Projects Report", self.generate_project_report),
            ("Workbook Report", self.generate_workbook_report),
            ("Data Source Report", self.generate_datasource_report),
            ("Favorites Report", self.generate_favorites_report),
            ("Subscriptions Report", self.generate_subscriptions_report),
            ("Master Report", self.generate_master_report),
            ("Approved Extensions", self.show_extensions_safe_list),
        ]

        for i, (label, command) in enumerate(buttons):
            row, col = divmod(i, 2)
            ctk.CTkButton(card, text=label, command=command, height=42).grid(
                row=row, column=col, sticky="ew", padx=18, pady=12
            )

    def save_report(self, df, filename, sheet_name):
        documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
        path = os.path.join(documents, filename)

        try:
            with pd.ExcelWriter(path) as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        except PermissionError:
            raise RuntimeError(
                f"Could not save the report because the file is open or locked:\n\n{path}\n\n"
                f"Please close the file and try again."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to save report:\n\n{path}\n\nReason: {e}")

        return path

    def run_report(self, func, status_text):
        self.saved_file_label.configure(text="")

        def success(path):
            self.saved_file_label.configure(
                text=f"Saved to: {path}",
                text_color=("#1f538d", "#7fb3ff")
            )

        def error(exc):
            self.saved_file_label.configure(
                text=str(exc),
                text_color=("#b00020", "#ff6b6b")
            )

        self.run_async(func, on_success=success, on_error=error, status_text=status_text)

    def generate_user_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_user_report(), 'Tableau Server - User Report.xlsx', 'Users'),
            "Generating user report..."
        )

    def generate_group_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_group_report(), 'Tableau Server - User Group Report.xlsx', 'Groups'),
            "Generating group report..."
        )
    
    def generate_permission_audit_report(self):
        self.run_report(
            lambda: self._save_permission_audit(),
            "Generating permission audit report."
        )

    def _save_permission_audit(self):
        reports = self.app.tableau.generate_permission_audit_report()
        documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
        path = os.path.join(documents, 'Tableau Server - Permission Audit Report.xlsx')
        with pd.ExcelWriter(path) as writer:
            for sheet_name, df in reports.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        return path

    def generate_project_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_project_report(), 'Tableau Server - Projects Report.xlsx', 'Projects'),
            "Generating project report..."
        )

    def generate_workbook_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_workbook_report(), 'Tableau Server - Workbook Report.xlsx', 'Workbooks'),
            "Generating workbook report..."
        )

    def generate_datasource_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_datasource_report(), 'Tableau Server - Data Source Report.xlsx', 'Data Sources'),
            "Generating data source report..."
        )

    def generate_favorites_report(self):
        ntlogin = self.prompt(
            "Favorites Report",
            "Enter User NTLogin:"
        )

        if not ntlogin:
            return

        self.run_report(
            lambda: self.save_report(
                self.app.tableau.generate_favorites_report(ntlogin),
                f'Tableau Server - Favorites Report - {ntlogin}.xlsx',
                'Favorites'
            ),
            f"Generating favorites report for {ntlogin}..."
        )

    def generate_subscriptions_report(self):
        self.run_report(
            lambda: self.save_report(self.app.tableau.generate_subscriptions_report(), 'Tableau Server - Subscription Report.xlsx', 'Subscriptions'),
            "Generating subscriptions report..."
        )

    def generate_master_report(self):
        if not self.confirm(
            "Long Running Report",
            "The Master Report may take several minutes to complete depending on the amount of Tableau content being queried.\n\nDo you want to continue?"
        ):
            return

        def task():
            reports = self.app.tableau.generate_master_report()
            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
            path = os.path.join(documents, 'Tableau Server - Master Report.xlsx')
            with pd.ExcelWriter(path) as writer:
                for sheet_name, df in reports.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            return path

        self.run_report(task, "Generating master report...")

    def show_extensions_safe_list(self):
        self.saved_file_label.configure(text="")

        def task():
            return self.app.tableau.get_extensions_site_safe_list()

        def success(safe_list):
            if not safe_list:
                message = "No approved extensions were returned."
            else:
                message = "\n".join(safe_list)

            self.app.show_text("Extensions List", message)
            self.set_status("Extensions loaded.")

        def error(exc):
            self.app.show_error(str(exc))

        self.run_async(
            task,
            on_success=success,
            on_error=error,
            status_text="Loading site extensions..."
        )