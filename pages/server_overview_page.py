import os
import json
from datetime import datetime

import customtkinter as ctk

from ui.base_page import BasePage
from ui.widgets import Card, SectionHeader, MetricCard


class ServerOverviewPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.job_failures_24h = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=0, column=0, sticky="nsew")
        self.scroll_area.grid_columnconfigure((0, 1), weight=1)

        SectionHeader(
            self.scroll_area,
            "Server Overview",
            "High-level Tableau site metrics and content summary"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12))

        top_bar = Card(self.scroll_area)
        top_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))
        top_bar.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(top_bar, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=18)

        self.summary_label = ctk.CTkLabel(
            inner,
            text="Click Refresh Overview to load current Tableau site metrics.",
            anchor="w",
            justify="left",
            text_color=("gray35", "gray75")
        )
        self.summary_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            inner,
            text="Refresh Overview",
            command=self.load_overview
        ).pack(side="right", padx=(12, 0))

        self.job_failure_banner = ctk.CTkButton(
            self.scroll_area,
            text="",
            fg_color="#8a1f1f",
            hover_color="#a83232",
            text_color="white",
            anchor="w",
            command=self.show_job_failures
        )
        self.job_failure_banner.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))
        self.job_failure_banner.grid_remove()

        self.cards = {}

        card_specs = [
            ("Users", 3, 0),
            ("Projects", 3, 1),

            ("Groups", 4, 0),
            ("Top Level Projects", 4, 1),

            ("Content Owners", 5, 0),
            ("Nested Projects", 5, 1),

            ("Subscriptions", 6, 0),
            ("Total Storage", 6, 1),

            ("Workbooks", 7, 0),
            ("Data Sources", 7, 1),

            ("Largest Workbook", 8, 0),
            ("Workbook Storage", 8, 1),
        ]

        for title, row, col in card_specs:
            card = MetricCard(self.scroll_area, title=title, value="—", subtitle="")
            padx = (24, 12) if col == 0 else (12, 24)
            card.grid(row=row, column=col, sticky="nsew", padx=padx, pady=12)
            self.cards[title] = card

        details = Card(self.scroll_area)
        details.grid(row=9, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 24))
        details.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            details,
            text="Connection Details",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        self.details_label = ctk.CTkLabel(
            details,
            text="No overview loaded.",
            justify="left",
            anchor="w"
        )
        self.details_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

    def _snapshot_path(self):
        return os.path.join(os.environ["USERPROFILE"], "tabmgmt_overview_snapshot.json")

    def _load_previous_snapshot(self):
        path = self._snapshot_path()

        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_snapshot(self, snapshot):
        path = self._snapshot_path()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

    def _build_snapshot(self, data):
        return {
            "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {
                "Users": int(data.get("users", 0) or 0),
                "Groups": int(data.get("groups", 0) or 0),
                "Content Owners": int(data.get("content_owners", 0) or 0),
                "Subscriptions": int(data.get("subscriptions", 0) or 0),
                "Projects": int(data.get("projects", 0) or 0),
                "Top Level Projects": int(data.get("top_level_projects", 0) or 0),
                "Nested Projects": int(data.get("nested_projects", 0) or 0),
                "Workbooks": int(data.get("workbooks", 0) or 0),
                "Data Sources": int(data.get("datasources", 0) or 0),
                "Workbook Storage MB": float(data.get("workbook_storage_mb", 0) or 0),
                "Data Source Storage MB": float(data.get("datasource_storage_mb", 0) or 0),
                "Total Storage MB": float(data.get("total_storage_mb", 0) or 0),
                "Largest Workbook MB": float(data.get("largest_workbook_size_mb", 0) or 0),
            }
        }

    def _format_number_delta(self, diff):
        if float(diff).is_integer():
            return f"{int(diff):,}"
        return f"{diff:,.2f}"

    def _format_storage_delta(self, diff_mb):
        abs_mb = abs(float(diff_mb or 0))

        if abs_mb >= 1024 * 1024:
            value = abs_mb / (1024 * 1024)
            unit = "TB"
        elif abs_mb >= 1024:
            value = abs_mb / 1024
            unit = "GB"
        else:
            value = abs_mb
            unit = "MB"

        return f"{value:,.2f} {unit}"

    def _trend_info(self, current_value, previous_value, is_storage=False):
        if previous_value is None:
            return "No prior snapshot", ("gray40", "gray70")

        try:
            current_value = float(current_value or 0)
            previous_value = float(previous_value or 0)
        except Exception:
            return "Trend unavailable", ("gray40", "gray70")

        diff = current_value - previous_value

        if diff > 0:
            delta_text = self._format_storage_delta(diff) if is_storage else self._format_number_delta(diff)
            return f"▲ +{delta_text} since last check", "#2e9d55"

        if diff < 0:
            delta_text = self._format_storage_delta(diff) if is_storage else self._format_number_delta(diff)
            return f"▼ -{delta_text} since last check", "#d9534f"

        return "■ No change since last check", ("gray40", "gray70")

    def _set_metric_card(
        self,
        card_name,
        display_value,
        subtitle,
        current_metric_value,
        previous_metrics,
        metric_key=None,
        is_storage=False
    ):
        metric_key = metric_key or card_name
        trend_text, trend_color = self._trend_info(
            current_metric_value,
            previous_metrics.get(metric_key),
            is_storage=is_storage
        )

        self.cards[card_name].set_data(
            display_value,
            subtitle,
            trend_text=trend_text,
            trend_color=trend_color
        )

    def _update_job_failure_banner(self, failures, error_message=""):
        self.job_failures_24h = failures or []

        if error_message:
            self.job_failure_banner.configure(
                text="⚠ Unable to check Tableau job failures from the last 24 hours. Click for details.",
                fg_color="#8a6d1f",
                hover_color="#a88428"
            )
            self.job_failure_banner.grid()
            return

        if not self.job_failures_24h:
            self.job_failure_banner.grid_remove()
            return

        count = len(self.job_failures_24h)
        label = "failure" if count == 1 else "failures"

        self.job_failure_banner.configure(
            text=f"⚠ {count} Tableau job {label} detected in the last 24 hours. Click to view details.",
            fg_color="#8a1f1f",
            hover_color="#a83232"
        )
        self.job_failure_banner.grid()

    def _format_job_failure_details(self):
        if not self.job_failures_24h:
            return "No Tableau job failures were found in the last 24 hours."

        lines = [
            "Tableau Job Failures - Last 24 Hours",
            f"Total Failures: {len(self.job_failures_24h)}",
            "",
        ]

        for idx, job in enumerate(self.job_failures_24h, start=1):
            lines.extend([
                f"{idx}. Job ID: {job.get('job_id', '')}",
                f"   Job Type: {job.get('job_type', '')}",
                f"   Status: {job.get('status', '')}",
                f"   Finish Code: {job.get('finish_code', '')}",
                f"   Created At: {job.get('created_at', '')}",
                f"   Started At: {job.get('started_at', '')}",
                f"   Ended At: {job.get('ended_at', '')}",
                f"   Title: {job.get('title', '')}",
                f"   Notes: {job.get('notes', '')}",
                f"   Progress: {job.get('progress', '')}",
                ""
            ])

        return "\n".join(lines)

    def show_job_failures(self):
        message = self._format_job_failure_details()
        self.app.show_text("Tableau Job Failures - Last 24 Hours", message)

    def load_overview(self):
        def task(progress=None):
            return self.app.tableau.generate_server_overview(progress_callback=progress)

        def success(data):
            previous_snapshot = self._load_previous_snapshot()
            previous_metrics = (previous_snapshot or {}).get("metrics", {})
            previous_checked = (previous_snapshot or {}).get("captured_at")

            current_snapshot = self._build_snapshot(data)
            current_checked = current_snapshot["captured_at"]

            self._set_metric_card(
                card_name="Users",
                display_value=f"{data['users']:,}",
                subtitle="Total users on the site",
                current_metric_value=data["users"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Projects",
                display_value=f"{data['projects']:,}",
                subtitle="All projects, including nested projects",
                current_metric_value=data["projects"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Groups",
                display_value=f"{data['groups']:,}",
                subtitle="Tableau groups on the site",
                current_metric_value=data["groups"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Top Level Projects",
                display_value=f"{data['top_level_projects']:,}",
                subtitle="Projects without a parent",
                current_metric_value=data["top_level_projects"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Content Owners",
                display_value=f"{data['content_owners']:,}",
                subtitle="Users owning workbooks or data sources",
                current_metric_value=data["content_owners"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Nested Projects",
                display_value=f"{data['nested_projects']:,}",
                subtitle="Projects with a parent project",
                current_metric_value=data["nested_projects"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Subscriptions",
                display_value=f"{data['subscriptions']:,}",
                subtitle="Configured subscriptions",
                current_metric_value=data["subscriptions"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Total Storage",
                display_value=data["total_storage_display"],
                subtitle="Workbook + data source storage",
                current_metric_value=float(data.get("total_storage_mb", 0) or 0),
                previous_metrics=previous_metrics,
                metric_key="Total Storage MB",
                is_storage=True
            )

            self._set_metric_card(
                card_name="Workbooks",
                display_value=f"{data['workbooks']:,}",
                subtitle="Published workbooks on the site",
                current_metric_value=data["workbooks"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Data Sources",
                display_value=f"{data['datasources']:,}",
                subtitle="Published data sources on the site",
                current_metric_value=data["datasources"],
                previous_metrics=previous_metrics
            )

            self._set_metric_card(
                card_name="Largest Workbook",
                display_value=data["largest_workbook_size_display"],
                subtitle=data["largest_workbook_name"],
                current_metric_value=float(data.get("largest_workbook_size_mb", 0) or 0),
                previous_metrics=previous_metrics,
                metric_key="Largest Workbook MB",
                is_storage=True
            )

            self._set_metric_card(
                card_name="Workbook Storage",
                display_value=data["workbook_storage_display"],
                subtitle="Total workbook storage used",
                current_metric_value=float(data.get("workbook_storage_mb", 0) or 0),
                previous_metrics=previous_metrics,
                metric_key="Workbook Storage MB",
                is_storage=True
            )

            self._update_job_failure_banner(
                data.get("job_failures_24h", []),
                data.get("job_failures_error", "")
            )

            latest_update = data["latest_workbook_update"]
            latest_update_text = str(latest_update) if latest_update else "N/A"
            previous_checked_text = previous_checked or "None"

            self.summary_label.configure(
                text=(
                    f"Loaded overview for site '{data['site_name']}' on {data['server_url']} | "
                    f"Current check: {current_checked} | Previous check: {previous_checked_text}"
                )
            )

            self.details_label.configure(
                text=(
                    f"Server URL: {data['server_url']}\n"
                    f"Site Name: {data['site_name']}\n"
                    f"Current Check: {current_checked}\n"
                    f"Previous Check: {previous_checked_text}\n"
                    f"Snapshot File: {self._snapshot_path()}\n"
                    f"Job Failures Last 24 Hours: {data.get('job_failures_24h_count', 0)}\n"
                    f"Workbook Storage: {data['workbook_storage_display']}\n"
                    f"Data Source Storage: {data['datasource_storage_display']}\n"
                    f"Total Storage: {data['total_storage_display']}\n"
                    f"Latest Workbook Update: {latest_update_text}\n"
                    f"Largest Workbook: {data['largest_workbook_name']} "
                    f"({data['largest_workbook_size_display']})"
                )
            )

            self._save_snapshot(current_snapshot)
            self.set_status("Server overview loaded.")

        self.run_async(
            task,
            on_success=success,
            status_text="Loading server overview..."
        )