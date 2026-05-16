import tkinter as tk
import ttkbootstrap as ttk
from tkinter import filedialog, messagebox
import threading
from autograde_tk.ui.theme import get_theme


class TDTPTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.course_content = ""
        self.current_worksheet = None
        self._build_ui()

    def _build_ui(self) -> None:
        theme = get_theme(self)
        top = ttk.Labelframe(self, text="Parametres TD/TP", padding=15, bootstyle="info")
        top.pack(side=tk.TOP, fill="x", pady=(0, 10))

        ttk.Label(top, text="Type :", font=theme.base_bold).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.kind_var = tk.StringVar(value="TD")
        self.kind_cb = ttk.Combobox(
            top, textvariable=self.kind_var, values=["TD", "TP"], state="readonly", width=8
        )
        self.kind_cb.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        ttk.Label(top, text="Support de cours (PDF) :", font=theme.base_bold).grid(
            row=1, column=0, sticky="nw", pady=10
        )
        pdf_row = ttk.Frame(top)
        pdf_row.grid(row=1, column=1, sticky="w", pady=10, padx=10)
        self.pdf_label = ttk.Label(pdf_row, text="Aucun fichier", font=theme.small)
        self.pdf_label.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(pdf_row, text="Importer PDF...", command=self._import_pdf, bootstyle="outline-primary").pack(
            side=tk.LEFT
        )

        ttk.Label(top, text="Consignes :", font=theme.base_bold).grid(
            row=2, column=0, sticky="nw", pady=5
        )
        self.instructions_text = tk.Text(top, height=4, width=70, font=theme.base, wrap="word")
        self.instructions_text.grid(row=2, column=1, sticky="ew", pady=5, padx=10)
        self.instructions_text.insert(
            "1.0",
            "Niveau licence. Langue : francais. Inclure des exercices progressifs et un corrige detaille.",
        )

        btn_row = ttk.Frame(top)
        btn_row.grid(row=3, column=1, sticky="e", pady=8, padx=10)
        ttk.Button(
            btn_row,
            text="Generer le TD/TP",
            command=self._generate_worksheet,
            bootstyle="success",
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_pdf = ttk.Button(
            btn_row,
            text="Telecharger en PDF",
            command=self._export_pdf,
            state=tk.DISABLED,
            bootstyle="primary",
            cursor="hand2",
        )
        self.btn_pdf.pack(side=tk.LEFT)

        top.columnconfigure(1, weight=1)

        mid = ttk.Labelframe(self, text="Apercu (Markdown)", padding=10, bootstyle="secondary")
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

        self.preview = tk.Text(mid, wrap="word", font=theme.base, undo=True)
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.preview.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview.configure(yscrollcommand=sb.set)

    def _import_pdf(self) -> None:
        filepath = filedialog.askopenfilename(
            filetypes=[("PDF", "*.pdf")],
            title="Support de cours pour generer un TD/TP",
        )
        if not filepath:
            return
        try:
            text = self.api_client.extract_text_from_pdf(filepath)
            if not text.strip():
                messagebox.showwarning("Attention", "Aucun texte extrait de ce PDF.")
                return
            self.course_content = text
            name = filepath.replace("\\", "/").split("/")[-1]
            self.pdf_label.config(text=name)
            messagebox.showinfo("OK", "Texte du PDF ajoute comme support de generation.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _selected_type(self) -> str:
        value = (self.kind_var.get() or "TD").strip().upper()
        return "tp" if value == "TP" else "td"

    def _generate_worksheet(self) -> None:
        if not self.course_content:
            messagebox.showwarning("Attention", "Veuillez importer un support de cours (PDF).")
            return

        instructions = self.instructions_text.get("1.0", tk.END).strip()
        worksheet_type = self._selected_type()

        self.btn_pdf.config(state=tk.DISABLED)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, "Generation en cours...\n")

        def task() -> None:
            try:
                data = self.api_client.generate_worksheet(
                    self.course_content, instructions, worksheet_type
                )
                self.after(0, lambda: self._on_worksheet_generated(data))
            except Exception as e:
                self.after(0, lambda err=e: self._on_worksheet_error(err))

        threading.Thread(target=task, daemon=True).start()

    def _export_pdf(self) -> None:
        if not self.current_worksheet:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Enregistrer le TD/TP en PDF",
        )
        if not path:
            return

        def task() -> None:
            try:
                pdf_bytes = self.api_client.export_worksheet_pdf(self.current_worksheet)
                with open(path, "wb") as f:
                    f.write(pdf_bytes)
                self.after(0, lambda: messagebox.showinfo("Export", f"PDF enregistre :\n{path}"))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Erreur", str(err)))

        threading.Thread(target=task, daemon=True).start()

    def _on_worksheet_generated(self, data: dict) -> None:
        self.current_worksheet = {
            "title": data["title"],
            "content_markdown": data["content_markdown"],
        }
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, f"# {data['title']}\n\n{data['content_markdown']}")
        self.btn_pdf.config(state=tk.NORMAL)
        messagebox.showinfo("Succes", "TD/TP genere avec succes !")

    def _on_worksheet_error(self, error: Exception) -> None:
        self.preview.delete("1.0", tk.END)
        messagebox.showerror("Erreur", f"Echec de la generation : {error}")
