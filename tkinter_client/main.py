import tkinter as tk

from autograde_tk.api_client import AutoGradeApiClient
from autograde_tk.ui.main_window import MainWindow


def run() -> None:
    root = tk.Tk()
    root.title("AutoGrade OCR - Tkinter")
    root.geometry("900x650")

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    client = AutoGradeApiClient(base_url="http://127.0.0.1:8000")
    MainWindow(root, client)

    root.mainloop()


if __name__ == "__main__":
    run()
