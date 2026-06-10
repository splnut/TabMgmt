import os
import pandas as pd
import customtkinter as ctk
from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, SearchableSingleSelect

class SubscriptionManagerPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.subscriptions = []
        self.filtered_subscriptions = []
        self.subscription_map = {}
        self.user_filter_values = []
        self.content_filter_values = []
        self.content_type_values = ["All", "Workbook", "View", "Unknown"]

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)

        SectionHeader(
            self,
            "Subscription Manager",
            "Load, review, filter, export, and delete Tableau subscriptions"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12))

        controls_card = Card(self)
        controls_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))
        controls_card.grid_columnconfigure(0, weight=1)

        controls_inner = ctk.CTkFrame(controls_card, fg_color="transparent")
        controls_inner.pack(fill="x", padx=18, pady=18)
        controls_inner.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(
            controls_inner,
            text="Load Subscriptions",
            command=self.load_subscriptions
        ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 12))

        ctk.CTkButton(
            controls_inner,
            text="Export Subscription Report",
            command=self.export_subscriptions_report
        ).grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 12))

        ctk.CTkButton(
            controls_inner,
            text="Clear Filters",
            command=self.clear_filters
        ).grid(row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 12))

        self.show_failed_only_var = ctk.BooleanVar(value=False)
        self.show_failed_only_check = ctk.CTkCheckBox(
            controls_inner,
            text="Show Failed / Suspicious Only",
            variable=self.show_failed_only_var,
            command=self.apply_filters
        )
        self.show_failed_only_check.grid(row=0, column=3, sticky="e", pady=(0, 12))

        filter_row = ctk.CTkFrame(controls_inner, fg_color="transparent")
        filter_row.grid(row=1, column=0, columnspan=4, sticky="ew")
        filter_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        user_filter_frame = ctk.CTkFrame(filter_row, fg_color="transparent")
        user_filter_frame.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(user_filter_frame, text="Filter by User").pack(anchor="w", pady=(0, 6))
        self.user_filter_menu = ctk.CTkOptionMenu(
            user_filter_frame,
            values=["All"],
            command=lambda _=None: self.apply_filters()
        )
        self.user_filter_menu.pack(fill="x")
        self.user_filter_menu.set("All")

        content_filter_frame = ctk.CTkFrame(filter_row, fg_color="transparent")
        content_filter_frame.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(content_filter_frame, text="Filter by Content").pack(anchor="w", pady=(0, 6))
        self.content_filter_menu = ctk.CTkOptionMenu(
            content_filter_frame,
            values=["All"],
            command=lambda _=None: self.apply_filters()
        )
        self.content_filter_menu.pack(fill="x")
        self.content_filter_menu.set("All")

        type_filter_frame = ctk.CTkFrame(filter_row, fg_color="transparent")
        type_filter_frame.grid(row=0, column=2, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(type_filter_frame, text="Filter by Content Type").pack(anchor="w", pady=(0, 6))
        self.content_type_menu = ctk.CTkOptionMenu(
            type_filter_frame,
            values=self.content_type_values,
            command=lambda _=None: self.apply_filters()
        )
        self.content_type_menu.pack(fill="x")
        self.content_type_menu.set("All")

        search_frame = ctk.CTkFrame(filter_row, fg_color="transparent")
        search_frame.grid(row=0, column=3, sticky="ew")
        ctk.CTkLabel(search_frame, text="Search").pack(anchor="w", pady=(0, 6))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search subject, user, content, or ID"
        )
        self.search_entry.pack(fill="x")

        results_card = Card(self)
        results_card.grid(row=2, column=0, sticky="nsew", padx=(24, 12), pady=(0, 12))
        results_card.grid_columnconfigure(0, weight=1)
        results_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            results_card,
            text="Subscriptions",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.subscription_select = SearchableSingleSelect(results_card, title="Loaded Subscriptions", height=420)
        self.subscription_select.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        detail_card = Card(self)
        detail_card.grid(row=2, column=1, sticky="nsew", padx=(12, 24), pady=(0, 12))
        detail_card.grid_columnconfigure(0, weight=1)
        detail_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            detail_card,
            text="Subscription Details",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.details_box = ctk.CTkTextbox(detail_card, height=420)
        self.details_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.details_box.insert("1.0", "Load subscriptions to begin.")
        self.details_box.configure(state="disabled")

        action_card = Card(self)
        action_card.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 24))
        action_card.grid_columnconfigure(0, weight=1)

        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=18, pady=18)

        ctk.CTkButton(
            action_inner,
            text="Preview Selected",
            command=self.preview_selected_subscription
        ).pack(side="left")

        ctk.CTkButton(
            action_inner,
            text="Delete Selected Subscription",
            command=self.delete_selected_subscription
        ).pack(side="right")

    def _set_details(self, text):
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.insert("1.0", text)
        self.details_box.configure(state="disabled")

    def _build_subscription_display(self, item):
        subject = str(item.get("subject", "")).strip() or "No Subject"
        owner_name = str(item.get("owner_name", "")).strip() or "Unknown User"
        content_name = str(item.get("content_name", "")).strip() or "Unknown Content"
        content_type = str(item.get("content_type", "")).strip() or "Unknown"

        return f"{subject} | {owner_name} | {content_type} | {content_name}"

    def _render_subscription_list(self):
        display_items = [self._build_subscription_display(item) for item in self.filtered_subscriptions]
        self.subscription_map = {
            self._build_subscription_display(item): item for item in self.filtered_subscriptions
        }
        self.subscription_select.set_items(display_items)

        if not display_items:
            self._set_details("No subscriptions match the current filters.")
            self.set_status("No subscriptions found for current filters.")
        else:
            self._set_details(f"{len(display_items)} subscription(s) loaded. Select one and click Preview Selected.")
            self.set_status(f"Loaded {len(display_items)} subscription(s).")

    def _refresh_filter_values(self):
        user_values = sorted({
            (str(item.get("owner_name", "")).strip() or "Unknown User")
            for item in self.subscriptions
        }, key=lambda x: x.lower())

        content_values = sorted({
            (str(item.get("content_name", "")).strip() or "Unknown Content")
            for item in self.subscriptions
        }, key=lambda x: x.lower())

        type_values = sorted({
            (str(item.get("content_type", "")).strip() or "Unknown")
            for item in self.subscriptions
        }, key=lambda x: x.lower())

        self.user_filter_values = ["All"] + user_values
        self.content_filter_values = ["All"] + content_values
        self.content_type_values = ["All"] + type_values

        self.user_filter_menu.configure(values=self.user_filter_values)
        self.content_filter_menu.configure(values=self.content_filter_values)
        self.content_type_menu.configure(values=self.content_type_values)

        if self.user_filter_menu.get() not in self.user_filter_values:
            self.user_filter_menu.set("All")
        if self.content_filter_menu.get() not in self.content_filter_values:
            self.content_filter_menu.set("All")
        if self.content_type_menu.get() not in self.content_type_values:
            self.content_type_menu.set("All")

    def load_subscriptions(self):
        def task(progress=None):
            if progress:
                progress("Loading subscriptions from Tableau...")
            return self.app.tableau.get_subscriptions_inventory()

        def success(subscriptions):
            self.subscriptions = subscriptions or []
            self.filtered_subscriptions = list(self.subscriptions)
            self._refresh_filter_values()
            self._render_subscription_list()

        def error(exc):
            self._set_details(str(exc))
            self.app.show_error(str(exc))

        self.run_async(
            task,
            on_success=success,
            on_error=error,
            status_text="Loading subscriptions..."
        )

    def apply_filters(self):
        user_filter = (self.user_filter_menu.get() or "All").strip()
        content_filter = (self.content_filter_menu.get() or "All").strip()
        type_filter = (self.content_type_menu.get() or "All").strip()
        search_text = self.search_var.get().strip().lower()
        failed_only = self.show_failed_only_var.get()

        filtered = []

        for item in self.subscriptions:
            owner_name = str(item.get("owner_name", "")).strip() or "Unknown User"
            content_name = str(item.get("content_name", "")).strip() or "Unknown Content"
            content_type = str(item.get("content_type", "")).strip() or "Unknown"
            subject = str(item.get("subject", "")).strip()
            subscription_id = str(item.get("subscription_id", "")).strip()
            suspicious = bool(item.get("is_suspicious", False))
            status_text = str(item.get("status", "")).strip().lower()

            if user_filter != "All" and owner_name != user_filter:
                continue
            if content_filter != "All" and content_name != content_filter:
                continue
            if type_filter != "All" and content_type != type_filter:
                continue

            if failed_only:
                if not suspicious and status_text not in ("failed", "suspended", "error"):
                    continue

            if search_text:
                haystack = " | ".join([
                    subscription_id,
                    subject,
                    owner_name,
                    content_name,
                    content_type,
                    str(item.get("owner_email", "")).strip(),
                ]).lower()
                if search_text not in haystack:
                    continue

            filtered.append(item)

        self.filtered_subscriptions = filtered
        self._render_subscription_list()

    def clear_filters(self):
        self.user_filter_menu.set("All")
        self.content_filter_menu.set("All")
        self.content_type_menu.set("All")
        self.show_failed_only_var.set(False)
        self.search_var.set("")
        self.filtered_subscriptions = list(self.subscriptions)
        self._render_subscription_list()

    def preview_selected_subscription(self):
        selected = self.subscription_select.get_selected()
        if not selected or selected not in self.subscription_map:
            return self.app.show_error("Select a valid subscription.")

        item = self.subscription_map[selected]

        detail_lines = [
            f"Subscription ID: {item.get('subscription_id', '')}",
            f"Subject: {item.get('subject', '')}",
            f"Owner Name: {item.get('owner_name', '')}",
            f"Owner Email: {item.get('owner_email', '')}",
            f"Owner Site Role: {item.get('owner_site_role', '')}",
            f"Content Type: {item.get('content_type', '')}",
            f"Content Name: {item.get('content_name', '')}",
            f"Content ID: {item.get('content_id', '')}",
            f"Schedule Name: {item.get('schedule_name', '')}",
            f"Status: {item.get('status', '')}",
            f"Suspicious: {'Yes' if item.get('is_suspicious', False) else 'No'}",
            f"Warning: {item.get('warning', '')}",
        ]

        self._set_details("\n".join(detail_lines))
        self.set_status("Subscription preview loaded.")

    def export_subscriptions_report(self):
        def task(progress=None):
            if progress:
                progress("Generating subscriptions report...")
            df = self.app.tableau.generate_subscriptions_report()

            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
            path = os.path.join(documents, 'Tableau Server - Subscription Report.xlsx')

            try:
                with pd.ExcelWriter(path) as writer:
                    df.to_excel(writer, sheet_name='Subscriptions', index=False)
            except PermissionError:
                raise RuntimeError(
                    f"Could not save the report because the file is open or locked:\n\n{path}\n\n"
                    f"Please close the file and try again."
                )

            return path

        def success(path):
            self.app.show_info(f"Subscription report saved successfully.\n\n{path}")
            self.set_status("Subscription report generated.")

        self.run_async(
            task,
            on_success=success,
            status_text="Generating subscriptions report..."
        )

    def delete_selected_subscription(self):
        selected = self.subscription_select.get_selected()
        if not selected or selected not in self.subscription_map:
            return self.app.show_error("Select a valid subscription.")

        item = self.subscription_map[selected]
        subscription_id = item.get("subscription_id", "")
        subject = item.get("subject", "") or "No Subject"
        owner_name = item.get("owner_name", "") or "Unknown User"

        if not subscription_id:
            return self.app.show_error("Selected subscription is missing an ID.")

        if not self.confirm(
            "Confirm Delete Subscription",
            f"Delete subscription '{subject}' for '{owner_name}'?\n\nSubscription ID: {subscription_id}"
        ):
            return

        def task(progress=None):
            if progress:
                progress("Deleting subscription...")
            self.app.tableau.delete_subscription(subscription_id)
            return subscription_id

        def success(_):
            self.subscriptions = [
                sub for sub in self.subscriptions
                if str(sub.get("subscription_id", "")).strip() != str(subscription_id).strip()
            ]
            self.apply_filters()
            self._set_details("Subscription deleted successfully.")
            self.app.show_info(f"Subscription {subscription_id} deleted successfully.")

        self.run_async(
            task,
            on_success=success,
            status_text="Deleting subscription..."
        )