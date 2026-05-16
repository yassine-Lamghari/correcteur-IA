import ttkbootstrap as ttk
from autograde_tk.api_client import AutoGradeApiClient
from autograde_tk.ui.main_window import MainWindow
from autograde_tk.ui.theme import apply_theme

def run() -> None:
    # Theme moderne inspire des apps Qt/PySide
    root = ttk.Window(themename="flatly")
    root.ui_theme = apply_theme(root)
    
    root.title("AutoGrade OCR - Modern UI")
    root.geometry("1000x800")
    root.minsize(800, 600)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    client = AutoGradeApiClient(base_url="http://127.0.0.1:8000")
    MainWindow(root, client)

    root.mainloop()


if __name__ == "__main__":
    run()
