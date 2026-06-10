import logging
import customtkinter as ctk

from config import AppConfig
from services.tableau_service import TableauService
from ui.dialogs import TextDisplayDialog
from ui.sidebar import Sidebar
from ui.widgets import StatusBar, LoadingOverlay

from pages.home_page import HomePage
from pages.settings_page import SettingsPage
from pages.workbook_refresh_page import WorkbookRefreshPage
from pages.connection_management_page import ConnectionManagementPage
from pages.user_management_page import UserManagementPage
from pages.permission_audit_page import PermissionAuditPage
from pages.subscription_manager_page import SubscriptionManagerPage
from pages.reports_page import ReportsPage
from pages.server_overview_page import ServerOverviewPage
from pages.tools_page import ToolsPage


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Tableau Site Management App")
        self.geometry("1400x880")
        self.minsize(1200, 760)

        ctk.set_appearance_mode("Dark")

        self.api_version = "3.25"
        self.app_config = AppConfig()
        self.tableau = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.loading_overlay = LoadingOverlay(self.main_container)

        self.pages = {
            "home": HomePage(self.main_container, self),
            "overview": ServerOverviewPage(self.main_container, self),
            "settings": SettingsPage(self.main_container, self),
            "workbooks": WorkbookRefreshPage(self.main_container, self),
            "connections": ConnectionManagementPage(self.main_container, self),
            "users": UserManagementPage(self.main_container, self),
            "permissions": PermissionAuditPage(self.main_container, self),
            "subscriptions": SubscriptionManagerPage(self.main_container, self),
            "tools": ToolsPage(self.main_container, self),
            "reports": ReportsPage(self.main_container, self),
        }

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        default_page = "settings"

        if self.app_config.is_valid():
            try:
                self.load_auth()
                self.status_bar.set("Connected to Tableau")
                default_page = "overview"
            except Exception as e:
                logging.exception("Failed to initialize Tableau connection")
                self.show_error(str(e))
                self.status_bar.set("Not connected")
                default_page = "settings"
        else:
            self.status_bar.set("Configure Tableau settings to begin")
            default_page = "settings"

        self.show_page(default_page)

    def load_auth(self):
        d = self.app_config.data
        self.tableau = TableauService(
            server_url=d["Tableau Server URL"],
            site_content_url=d["Tableau Site Name"],
            token_name=d["Access Token Name"],
            token_value=d["Access Token"],
            api_version=self.api_version
        )
        if not self.tableau.test_auth():
            raise RuntimeError("Failed to authenticate to Tableau Server.")

    def show_page(self, key):
        self.sidebar.set_active(key)
        self.pages[key].tkraise()

    def show_info(self, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Info")
        dialog.geometry("520x230")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=message, wraplength=460, justify="left").pack(
            padx=24, pady=(30, 20)
        )
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=10)

    def show_error(self, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Error")
        dialog.geometry("520x230")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=message,
            wraplength=460,
            justify="left",
            text_color="#ff6b6b"
        ).pack(padx=24, pady=(30, 20))
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=10)

    def show_text(self, title, message):
        dialog = TextDisplayDialog(self, title, message)
        self.wait_window(dialog)