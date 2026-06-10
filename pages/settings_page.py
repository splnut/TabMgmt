import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, FormRow


class SettingsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.grid_columnconfigure(0, weight=1)

        SectionHeader(
            self,
            "Settings",
            "Manage Tableau authentication settings"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        self.settings_card = Card(self)
        self.settings_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 24))
        self.settings_card.grid_columnconfigure(0, weight=1)

        self.entries = {}

        form = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
        form.grid_columnconfigure(0, weight=1)

        settings_fields = [
            "Tableau Server URL",
            "Tableau Site Name",
            "Access Token Name",
            "Access Token",
            "Email Address",
            "NTLogin",
        ]

        for i, field in enumerate(settings_fields):
            show_value = "*" if field == "Access Token" else ""
            row = FormRow(form, field, show=show_value)
            row.grid(row=i, column=0, sticky="ew", pady=6)

            row.entry.insert(0, self.app.app_config.get(field, ""))
            self.entries[field] = row.entry

        button_row = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        button_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        button_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            button_row,
            text="Test & Save",
            command=self.save_settings
        ).grid(row=0, column=1, sticky="e")

    def save_settings(self):
        for key, entry in self.entries.items():
            self.app.app_config.set(key, entry.get().strip())
        self.app.app_config.save()

        def task(progress=None):
            self.app.load_auth()

        def success(_):
            self.app.show_info("Configuration saved and authenticated successfully.")
            self.set_status("Connected to Tableau")

        self.run_async(
            task,
            on_success=success,
            on_error=lambda e: self.app.show_error(f"Authentication failed: {e}"),
            status_text="Testing Tableau connection..."
        )