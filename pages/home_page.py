import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader


class HomePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.grid_columnconfigure((0, 1), weight=1)

        SectionHeader(self, "Tableau Site Management", "Site Admin Functions").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12)
        )

        cards = [
            ("Workbook Refresh", "Load projects, filter workbooks, and trigger refreshes.", "workbooks"),
            ("Connection Management", "Update connection server names and credentials for workbooks and published data sources.", "connections"),
            ("User Management", "Add users to groups or remove users from the site.", "users"),
            ("Reports", "Generate Excel reports in your Documents folder.", "reports"),
            ("Permission Audit", "Audit project, workbook, and published data source permissions and export findings.", "permissions"),
            ("Subscription Manager", "Load, review, export, and delete Tableau subscriptions", "subscriptions"),
            ("Tools", "Administrative Tasks. Use with Caution.","tools"),
            ("Settings", "Configure Tableau connection settings.", "settings"),
        ]

        for i, (title, description, page_key) in enumerate(cards):
            r, c = divmod(i, 2)

            card = Card(self)
            card.grid(row=r + 1, column=c, sticky="nsew", padx=24, pady=12)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkButton(
                card,
                text=title,
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w",
                fg_color="transparent",
                hover_color=("gray75", "gray25"),
                text_color=("black", "white"),
                command=lambda k=page_key: self.app.show_page(k)
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

            ctk.CTkLabel(
                card,
                text=description,
                wraplength=420,
                justify="left"
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))