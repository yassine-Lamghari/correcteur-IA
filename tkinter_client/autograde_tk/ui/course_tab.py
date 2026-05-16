import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox, filedialog
import threading
from autograde_tk.ui.theme import get_theme


class CourseTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.current_course: dict | None = None
        self.source_material = ""
        self._build_ui()

    def _build_ui(self) -> None:
        theme = get_theme(self)
        top = ttk.Labelframe(self, text="Paramètres du cours (Gemini)", padding=15, bootstyle="info")
        top.pack(side=tk.TOP, fill="x", pady=(0, 10))

        ttk.Label(top, text="Sujet / titre du cours :", font=theme.base_bold).grid(
            row=0, column=0, sticky="nw", pady=5
        )
        self.topic_text = tk.Text(top, height=2, width=70, font=theme.base, wrap="word")
        self.topic_text.grid(row=0, column=1, sticky="ew", pady=5, padx=10)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Consignes (niveau, durée, style, langue) :", font=theme.base_bold).grid(
            row=1, column=0, sticky="nw", pady=5
        )
        self.instructions_text = tk.Text(top, height=4, width=70, font=theme.base, wrap="word")
        self.instructions_text.grid(row=1, column=1, sticky="ew", pady=5, padx=10)
        self.instructions_text.insert(
            "1.0",
            "Niveau : licence / master. Langue : français. Inclure définitions, exemples numériques ou cas pratiques, "
            "exercices avec corrigés détaillés.",
        )

        ttk.Label(top, text="Support optionnel (PDF) :", font=theme.base_bold).grid(
            row=2, column=0, sticky="nw", pady=8
        )
        pdf_row = ttk.Frame(top)
        pdf_row.grid(row=2, column=1, sticky="w", pady=8, padx=10)
        self.pdf_label = ttk.Label(pdf_row, text="Aucun fichier", font=theme.small)
        self.pdf_label.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(pdf_row, text="Importer PDF…", command=self._import_pdf, bootstyle="outline-primary").pack(
            side=tk.LEFT
        )

        btn_row = ttk.Frame(top)
        btn_row.grid(row=3, column=1, sticky="e", pady=8, padx=10)
        ttk.Button(
            btn_row,
            text="✨ Générer le cours complet",
            command=self._generate_course,
            bootstyle="success",
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_pdf = ttk.Button(
            btn_row,
            text="📥 Télécharger en PDF",
            command=self._export_pdf,
            state=tk.DISABLED,
            bootstyle="primary",
            cursor="hand2",
        )
        self.btn_pdf.pack(side=tk.LEFT)

        mid = ttk.Labelframe(self, text="Aperçu du cours (Markdown)", padding=10, bootstyle="secondary")
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

        self.preview = tk.Text(mid, wrap="word", font=theme.base, undo=True)
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.preview.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview.configure(yscrollcommand=sb.set)

    def _import_pdf(self) -> None:
        filepath = filedialog.askopenfilename(
            filetypes=[("PDF", "*.pdf")],
            title="Texte source pour enrichir le cours",
        )
        if not filepath:
            return
        try:
            text = self.api_client.extract_text_from_pdf(filepath)
            if not text.strip():
                messagebox.showwarning("Attention", "Aucun texte extrait de ce PDF.")
                return
            self.source_material = text
            name = filepath.replace("\\", "/").split("/")[-1]
            self.pdf_label.config(text=name)
            messagebox.showinfo("OK", "Texte du PDF ajouté comme matériel source pour la génération.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _generate_course(self) -> None:
        topic = self.topic_text.get("1.0", tk.END).strip()
        if len(topic) < 3:
            messagebox.showwarning("Attention", "Indiquez un sujet ou titre de cours (au moins quelques mots).")
            return
        instructions = self.instructions_text.get("1.0", tk.END).strip()
        self.btn_pdf.config(state=tk.DISABLED)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, "Génération en cours…\n")

        def task() -> None:
            try:
                data = self.api_client.generate_course(topic, instructions, self.source_material)
                self.after(0, lambda: self._on_course_generated(data))
            except Exception as e:
                self.after(0, lambda err=e: self._on_course_error(err))

        threading.Thread(target=task, daemon=True).start()

    def _export_pdf(self) -> None:
        if not self.current_course:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Enregistrer le cours en PDF",
        )
        if not path:
            return

        def task() -> None:
            try:
                pdf_bytes = self.api_client.export_course_pdf(self.current_course)
                with open(path, "wb") as f:
                    f.write(pdf_bytes)
                self.after(0, lambda: messagebox.showinfo("Export", f"PDF enregistré :\n{path}"))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Erreur", str(err)))

        threading.Thread(target=task, daemon=True).start()

    def _on_course_generated(self, data: dict) -> None:
        self.current_course = {"title": data["title"], "content_markdown": data["content_markdown"]}
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, f"# {data['title']}\n\n{data['content_markdown']}")
        self.btn_pdf.config(state=tk.NORMAL)
        messagebox.showinfo("Succès", "Cours généré. Vous pouvez l’exporter en PDF.")

    def _on_course_error(self, error: Exception) -> None:
        self.preview.delete("1.0", tk.END)
        messagebox.showerror("Erreur", f"Échec de la génération : {error}")
