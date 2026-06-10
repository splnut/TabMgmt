import customtkinter as ctk


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0)
        self.app = app

        self.header_label = ctk.CTkLabel(
            self,
            text="Tableau Admin",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.grid(row=0, column=0, sticky="w", padx=18, pady=(22, 16))

        items = [
            ("Home", "home"),
            ("Server Overview", "overview"),
            ("Workbook Refresh", "workbooks"),
            ("Connection Mgmt", "connections"),
            ("User Mgmt", "users"),
            ("Permission Audit", "permissions"),
            ("Subscriptions", "subscriptions"),
            ("Tools", "tools"),
            ("Reports", "reports"),
        ]

        self.buttons = {}
        for idx, (label, key) in enumerate(items, start=1):
            btn = ctk.CTkButton(
                self,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda k=key: app.show_page(k)
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=12, pady=6)
            self.buttons[key] = btn

        settings_row = len(items) + 1
        settings_button = ctk.CTkButton(
            self,
            text="Settings",
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda: app.show_page("settings")
        )
        settings_button.grid(row=settings_row, column=0, sticky="ew", padx=12, pady=6)
        self.buttons["settings"] = settings_button

        self.grid_rowconfigure(settings_row + 1, weight=1)

        self.appearance_label = ctk.CTkLabel(
            self,
            text="Appearance",
            text_color=("gray40", "gray70")
        )
        self.appearance_label.grid(row=settings_row + 2, column=0, sticky="w", padx=16, pady=(12, 6))

        self.appearance_menu = ctk.CTkOptionMenu(
            self,
            values=["System", "Light", "Dark"],
            command=self.change_appearance
        )
        self.appearance_menu.grid(row=settings_row + 3, column=0, sticky="ew", padx=12, pady=6)
        self.appearance_menu.set(ctk.get_appearance_mode())

        exit_row = settings_row + 4
        ctk.CTkButton(
            self,
            text="Exit",
            fg_color="#b33939",
            hover_color="#922b2b",
            command=app.destroy
        ).grid(row=exit_row, column=0, sticky="ew", padx=12, pady=(8, 20))

        self.update_text_color()

    def set_active(self, key):
        for page_key, btn in self.buttons.items():
            if page_key == key:
                btn.configure(
                    fg_color=("gray65", "#1f6aa5"),
                    text_color=("black", "white")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("black", "white")
                )

    def change_appearance(self, mode):
        ctk.set_appearance_mode(mode)
        self.update_text_color()
        self.set_active(
            next((k for k, b in self.buttons.items() if b.cget("fg_color") != "transparent"), "home")
        )

    def update_text_color(self):
        text_color = ("black", "white")
        self.header_label.configure(text_color=text_color)

        for btn in self.buttons.values():
            btn.configure(text_color=text_color)

        self.appearance_label.configure(text_color=("gray40", "gray70"))