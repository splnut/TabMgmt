import customtkinter as ctk
from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, FormRow, SearchableMultiSelect, SearchableSingleSelect

class UserManagementPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.groups = []
        self.user_map = {}

        self.grid_columnconfigure((0, 1), weight=1)

        SectionHeader(self, "User Management", "Manage site users and Tableau group membership").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12)
        )

        add_card = Card(self)
        add_card.grid(row=1, column=0, sticky="nsew", padx=(24, 12), pady=(12, 24))
        add_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(add_card, text="Add User", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=18, pady=(18, 8)
        )

        add_form = ctk.CTkFrame(add_card, fg_color="transparent")
        add_form.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        add_form.grid_columnconfigure(0, weight=1)
        add_form.grid_rowconfigure(4, weight=1)

        top_btns = ctk.CTkFrame(add_form, fg_color="transparent")
        top_btns.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(top_btns, text="Load Groups", command=self.load_groups).grid(row=0, column=0, sticky="w")

        ntlogin_row = FormRow(add_form, "NTLogin")
        ntlogin_row.grid(row=1, column=0, sticky="ew", pady=8)
        self.ntlogin_entry = ntlogin_row.entry

        options_row = ctk.CTkFrame(add_form, fg_color="transparent")
        options_row.grid(row=2, column=0, sticky="ew", pady=8)
        options_row.grid_columnconfigure(3, weight=1)

        self.bulk_upload_var = ctk.BooleanVar(value=False)
        self.bulk_upload_check = ctk.CTkCheckBox(
            options_row,
            text="Bulk Upload",
            variable=self.bulk_upload_var,
            command=self.on_bulk_upload_toggle
        )
        self.bulk_upload_check.grid(row=0, column=0, sticky="w", padx=(0, 24))

        ctk.CTkLabel(options_row, text="License Type", width=100, anchor="w").grid(
            row=0, column=1, sticky="w", padx=(0, 8)
        )

        self.license_type_menu = ctk.CTkOptionMenu(
            options_row,
            values=["Viewer", "Explorer", "Creator"]
        )
        self.license_type_menu.grid(row=0, column=2, sticky="w")
        self.license_type_menu.set("Viewer")

        self.ntlogin_help = ctk.CTkLabel(
            add_form,
            text="Enter one NTLogin.",
            text_color=("gray40", "gray70"),
            anchor="w",
            justify="left"
        )
        self.ntlogin_help.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.group_box = SearchableMultiSelect(add_form, title="Groups", height=280)
        self.group_box.grid(row=4, column=0, sticky="nsew", pady=8)

        self.add_user_button = ctk.CTkButton(add_form, text="Add User", command=self.add_user)
        self.add_user_button.grid(row=5, column=0, sticky="e", pady=(12, 0))

        remove_card = Card(self)
        remove_card.grid(row=1, column=1, sticky="nsew", padx=(12, 24), pady=(12, 24))
        remove_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(remove_card, text="Remove User", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=18, pady=(18, 8)
        )

        remove_form = ctk.CTkFrame(remove_card, fg_color="transparent")
        remove_form.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        remove_form.grid_columnconfigure(0, weight=1)
        remove_form.grid_rowconfigure(1, weight=1)

        top_btns2 = ctk.CTkFrame(remove_form, fg_color="transparent")
        top_btns2.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_btns2.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(top_btns2, text="Load Users", command=self.load_users).grid(row=0, column=0, sticky="w")

        self.user_select = SearchableSingleSelect(remove_form, title="Users", height=360)
        self.user_select.grid(row=1, column=0, sticky="nsew", pady=8)

        ctk.CTkButton(remove_form, text="Remove User", command=self.remove_user).grid(
            row=2, column=0, sticky="e", pady=(12, 0)
        )

    def on_bulk_upload_toggle(self):
        if self.bulk_upload_var.get():
            self.ntlogin_help.configure(
                text="Bulk Upload enabled: enter comma-separated NTLogin values."
            )
            self.add_user_button.configure(text="Bulk Add Users")
        else:
            self.ntlogin_help.configure(
                text="Enter one NTLogin."
            )
            self.add_user_button.configure(text="Add User")

    def load_groups(self):
        def task():
            return [g.name for g in self.app.tableau.get_groups()]

        def success(groups):
            self.groups = groups
            self.group_box.set_items(groups)
            self.set_status(f"Loaded {len(groups)} groups.")

        self.run_async(task, on_success=success, status_text="Loading groups...")

    def add_user(self):
        ntlogin_text = self.ntlogin_entry.get().strip()
        selected_groups = self.group_box.get_selected()
        site_role = self.license_type_menu.get().strip() or "Viewer"
        is_bulk = self.bulk_upload_var.get()

        if not ntlogin_text:
            return self.app.show_error("Enter NTLogin.")

        if is_bulk:
            usernames = [x.strip() for x in ntlogin_text.split(",") if x.strip()]
            if not usernames:
                return self.app.show_error("Enter at least one valid NTLogin.")
        else:
            usernames = [ntlogin_text]

        if not self.confirm(
            "Confirm Add User" if not is_bulk else "Confirm Bulk Add Users",
            (
                f"{'Add user' if not is_bulk else 'Add users'} with license type '{site_role}'?\n\n"
                f"User count: {len(usernames)}\n"
                f"Selected groups: {len(selected_groups)}"
            )
        ):
            return

        def task(progress=None):
            if is_bulk:
                return self.app.tableau.bulk_add_users(
                    usernames=usernames,
                    site_role=site_role,
                    group_names=selected_groups
                )
            else:
                return self.app.tableau.add_user(
                    usernames[0],
                    site_role=site_role,
                    group_names=selected_groups
                )

        def success(result):
            if is_bulk:
                added = result.get("added", [])
                skipped = result.get("skipped", [])
                failed = result.get("failed", [])

                message_lines = [
                    "Bulk add complete.",
                    "",
                    f"Added: {len(added)}",
                    f"Skipped: {len(skipped)}",
                    f"Failed: {len(failed)}",
                ]

                if added:
                    preview_added = added[:20]
                    message_lines.append("")
                    message_lines.append("Added:")
                    for username in preview_added:
                        message_lines.append(f" - {username}")

                if skipped:
                    message_lines.append("")
                    message_lines.append("Skipped:")
                    for item in skipped[:20]:
                        message_lines.append(f" - {item['username'] or '[blank]'}: {item['reason']}")

                if failed:
                    message_lines.append("")
                    message_lines.append("Failed:")
                    for item in failed[:20]:
                        message_lines.append(f" - {item['username']}: {item['reason']}")

                self.app.show_info("\n".join(message_lines))
            else:
                self.app.show_info(f"User {usernames[0]} added successfully with {site_role} license.")

        self.run_async(
            task,
            on_success=success,
            status_text="Adding users..." if is_bulk else "Adding user..."
        )

    def load_users(self):
        def task():
            return self.app.tableau.get_users_display_map()

        def success(user_map):
            self.user_map = user_map
            self.user_select.set_items(list(user_map.keys()))
            self.set_status(f"Loaded {len(user_map)} users.")

        self.run_async(task, on_success=success, status_text="Loading users...")

    def remove_user(self):
        selected = self.user_select.get_selected()
        if not selected or selected not in self.user_map:
            return self.app.show_error("Select a valid user.")

        user = self.user_map[selected]

        if not self.confirm(
            "Confirm Remove User",
            f"Remove user '{user.fullname}' from the Tableau site?"
        ):
            return

        def task():
            self.app.tableau.remove_user(user.id)

        def success(_):
            self.app.show_info(f"{user.fullname} was removed successfully.")

        self.run_async(task, on_success=success, status_text="Removing user...")