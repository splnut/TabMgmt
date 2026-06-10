import customtkinter as ctk


class Card(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, corner_radius=14, **kwargs)


class SectionHeader(ctk.CTkFrame):
    def __init__(self, parent, title, subtitle=""):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                text_color=("gray40", "gray70")
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))


class CollapsibleCard(Card):
    def __init__(self, parent, title, expanded=True, **kwargs):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.expanded = expanded
        self.title = title

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        self.header.grid_columnconfigure(0, weight=1)

        self.title_button = ctk.CTkButton(
            self.header,
            text=f"▼ {title}" if expanded else f"▶ {title}",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("black", "white"),
            command=self.toggle
        )
        self.title_button.grid(row=0, column=0, sticky="w")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.body.grid_columnconfigure(0, weight=1)

        if not expanded:
            self.body.grid_remove()

    def toggle(self):
        if self.expanded:
            self.body.grid_remove()
            self.title_button.configure(text=f"▶ {self.title}")
            self.expanded = False
        else:
            self.body.grid()
            self.title_button.configure(text=f"▼ {self.title}")
            self.expanded = True


class FormRow(ctk.CTkFrame):
    def __init__(self, parent, label_text, show=""):
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.label = ctk.CTkLabel(
            self,
            text=label_text,
            width=180,
            anchor="w"
        )
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=4)

        self.entry = ctk.CTkEntry(self, show=show)
        self.entry.grid(row=0, column=1, sticky="ew", pady=4)


class LoadingOverlay(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color=("gray85", "gray15"))
        self.place_forget()

        self.container = ctk.CTkFrame(self, corner_radius=16)
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        self.progress = ctk.CTkProgressBar(self.container, mode="indeterminate", width=240)
        self.progress.pack(padx=24, pady=(24, 12))

        self.label = ctk.CTkLabel(self.container, text="Working...")
        self.label.pack(padx=24, pady=(0, 24))

    def show(self, text="Working..."):
        self.label.configure(text=text)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self.progress.start()

    def hide(self):
        self.progress.stop()
        self.place_forget()


class StatusBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.label.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

    def set(self, text):
        self.label.configure(text=text)


class SearchableMultiSelect(ctk.CTkFrame):
    def __init__(self, parent, title="Items", height=280):
        super().__init__(parent, fg_color="transparent")
        self.items = []
        self.filtered_items = []
        self.vars = {}

        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search...")
        self.search_entry.pack(fill="x", pady=(0, 8))

        top_actions = ctk.CTkFrame(self, fg_color="transparent")
        top_actions.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(top_actions, text="Select All", width=90, command=self.select_all).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(top_actions, text="Clear", width=90, command=self.clear_selection).pack(
            side="left"
        )

        self.scroll = ctk.CTkScrollableFrame(self, height=height)
        self.scroll.pack(fill="both", expand=True)

        self.empty_label = None

    def set_items(self, items):
        selected = set(self.get_selected())
        self.items = list(items)
        self.filtered_items = list(items)

        self.vars = {}
        for item in self.items:
            var = ctk.BooleanVar(value=item in selected)
            self.vars[item] = var

        self._render()

    def _on_search(self, *args):
        text = self.search_var.get().strip().lower()
        if not text:
            self.filtered_items = list(self.items)
        else:
            self.filtered_items = [item for item in self.items if text in item.lower()]
        self._render()

    def _render(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            self.empty_label = ctk.CTkLabel(
                self.scroll,
                text="No matching items.",
                text_color=("gray45", "gray65")
            )
            self.empty_label.pack(anchor="w", padx=4, pady=4)
            return

        for item in self.filtered_items:
            chk = ctk.CTkCheckBox(self.scroll, text=item, variable=self.vars[item])
            chk.pack(anchor="w", fill="x", padx=4, pady=3)

    def get_selected(self):
        return [item for item, var in self.vars.items() if var.get()]

    def select_all(self):
        for item in self.filtered_items:
            self.vars[item].set(True)

    def clear_selection(self):
        for var in self.vars.values():
            var.set(False)


class SearchableSingleSelect(ctk.CTkFrame):
    def __init__(self, parent, title="Items", height=260):
        super().__init__(parent, fg_color="transparent")
        self.items = []
        self.filtered_items = []
        self.selected_value = None

        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search...")
        self.search_entry.pack(fill="x", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, height=height)
        self.scroll.pack(fill="both", expand=True)

    def set_items(self, items):
        self.items = list(items)
        self.filtered_items = list(items)
        self._render()

    def _on_search(self, *args):
        text = self.search_var.get().strip().lower()
        if not text:
            self.filtered_items = list(self.items)
        else:
            self.filtered_items = [item for item in self.items if text in item.lower()]
        self._render()

    def _select(self, value):
        self.selected_value = value
        self._render()

    def _render(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            ctk.CTkLabel(
                self.scroll,
                text="No matching items.",
                text_color=("gray45", "gray65")
            ).pack(anchor="w", padx=4, pady=4)
            return

        for item in self.filtered_items:
            btn = ctk.CTkButton(
                self.scroll,
                text=item,
                anchor="w",
                fg_color=("gray78", "gray23") if item == self.selected_value else "transparent",
                hover_color=("gray70", "gray28"),
                text_color=("black", "white"),
                command=lambda x=item: self._select(x)
            )
            btn.pack(fill="x", padx=4, pady=3)

    def get_selected(self):
        return self.selected_value

    def clear(self):
        self.selected_value = None
        self._render()


class MetricCard(Card):
    def __init__(self, parent, title, value="", subtitle="", trend_text=""):
        super().__init__(parent)
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray35", "gray75"),
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w"
        )
        self.value_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 4))

        self.trend_label = ctk.CTkLabel(
            self,
            text=trend_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=260
        )
        self.trend_label.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 2))

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
            justify="left",
            wraplength=260
        )
        self.subtitle_label.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))

    def set_data(self, value, subtitle="", trend_text="", trend_color=None):
        self.value_label.configure(text=value)
        self.subtitle_label.configure(text=subtitle)

        self.trend_label.configure(
            text=trend_text,
            text_color=trend_color if trend_color else ("gray40", "gray70")
        )