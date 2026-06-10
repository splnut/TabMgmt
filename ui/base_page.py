import logging
import threading
import customtkinter as ctk

from ui.dialogs import ConfirmDialog, PromptDialog


class BasePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

    def set_status(self, text):
        self.app.status_bar.set(text)

    def run_async(self, func, on_success=None, on_error=None, status_text="Working..."):
        self.app.loading_overlay.show(status_text)
        self.set_status(status_text)

        def progress(message):
            self.after(0, lambda m=message: self.app.loading_overlay.show(m))
            self.after(0, lambda m=message: self.set_status(m))

        def worker():
            try:
                try:
                    result = func(progress)
                except TypeError:
                    result = func()
                self.after(0, lambda r=result: on_success(r) if on_success else None)
            except Exception as exc:
                logging.exception("Async operation failed")
                if on_error:
                    self.after(0, lambda e=exc: on_error(e))
                else:
                    self.after(0, lambda msg=str(exc): self.app.show_error(msg))
            finally:
                self.after(0, self.app.loading_overlay.hide)
                self.after(0, lambda: self.set_status("Ready"))

        threading.Thread(target=worker, daemon=True).start()

    def confirm(self, title, message):
        dialog = ConfirmDialog(self.app, title, message)
        self.wait_window(dialog)
        return dialog.result

    def prompt(self, title, message):
        dialog = PromptDialog(self.app, title, message)
        self.wait_window(dialog)
        return dialog.result