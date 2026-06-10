import customtkinter as ctk


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.geometry("460x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text=message, wraplength=400, justify="left").pack(
            padx=24, pady=(28, 20)
        )

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10)

        ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, fg_color="gray").pack(
            side="left", padx=8
        )
        ctk.CTkButton(button_frame, text="Confirm", command=self.confirm).pack(
            side="left", padx=8
        )

    def confirm(self):
        self.result = True
        self.destroy()

    def cancel(self):
        self.result = False
        self.destroy()


class PromptDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.geometry("460x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text=prompt, wraplength=400, justify="left").pack(
            padx=24, pady=(28, 12)
        )

        self.entry = ctk.CTkEntry(self, width=320)
        self.entry.pack(padx=24, pady=(0, 20))
        self.entry.focus()

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10)

        ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, fg_color="gray").pack(
            side="left", padx=8
        )
        ctk.CTkButton(button_frame, text="OK", command=self.submit).pack(
            side="left", padx=8
        )

        self.bind("<Return>", lambda event: self.submit())
        self.bind("<Escape>", lambda event: self.cancel())

    def submit(self):
        value = self.entry.get().strip()
        self.result = value if value else None
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


class TextDisplayDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()

        textbox = ctk.CTkTextbox(self, wrap="word")
        textbox.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        textbox.insert("1.0", message)
        textbox.configure(state="disabled")

        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=(0, 20))