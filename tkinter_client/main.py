import ttkbootstrap as ttk
from autograde_tk.api_client import AutoGradeApiClient
from autograde_tk.ui.main_window import MainWindow

def run() -> None:
    # Utilisation de ttkbootstrap pour un design moderne, thème par défaut litera pour un look propre et clair
    root = ttk.Window(themename="litera")
    
    # Configuration globale de la police
    style = ttk.Style()
    style.configure(".", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10, "bold"))
    style.configure("TLabel", font=("Segoe UI", 10))
    
    root.title("AutoGrade OCR - Modern UI")
    root.geometry("1000x800")
    root.minsize(800, 600)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    client = AutoGradeApiClient(base_url="http://127.0.0.1:8080")
    MainWindow(root, client)

    root.mainloop()


if __name__ == "__main__":
    run()
