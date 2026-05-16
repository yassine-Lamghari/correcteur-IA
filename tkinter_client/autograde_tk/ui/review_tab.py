import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk

from autograde_tk.ui.theme import get_theme


class ReviewTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.classes = []
        self.subjects = []
        self.current_class = None
        self.current_subject = None
        self.review_items = []
        self._build_ui()
        self._load_classes()

    def _build_ui(self) -> None:
        theme = get_theme(self)

        top = ttk.Labelframe(self, text="Copie a verifier", padding=10, bootstyle="info")
        top.pack(side=tk.TOP, fill="x", pady=(0, 10))

        ttk.Label(top, text="Classe:", font=theme.base_bold).grid(row=0, column=0, sticky="w")
        self.cb_class = ttk.Combobox(top, state="readonly", width=18, bootstyle="primary")
        self.cb_class.grid(row=0, column=1, sticky="w")
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)

        ttk.Label(top, text="Matiere:", font=theme.base_bold).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.cb_subject = ttk.Combobox(top, state="readonly", width=18, bootstyle="primary")
        self.cb_subject.grid(row=0, column=3, sticky="w")
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)

        grid = ttk.Labelframe(self, text="Queue", padding=10, bootstyle="secondary")
        grid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        grid.columnconfigure(0, weight=2)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)

        columns = ("ID", "Nom", "Note", "OCR", "Qualite", "Raison", "Statut")
        self.tree = ttk.Treeview(grid, columns=columns, show="headings", height=10, bootstyle="warning")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        sb = ttk.Scrollbar(grid, orient=tk.VERTICAL, command=self.tree.yview)
        sb.grid(row=0, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.raw_text = tk.Text(grid, wrap="word", height=8, font=theme.mono)
        self.raw_text.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        action = ttk.Frame(self)
        action.pack(side=tk.TOP, fill="x", pady=(8, 0))
        ttk.Button(action, text="Rafraichir", command=self._refresh_queue, bootstyle="secondary").pack(
            side=tk.LEFT
        )
        ttk.Button(action, text="Marquer resolu", command=self._mark_resolved, bootstyle="success").pack(side=tk.RIGHT)

    def _load_classes(self) -> None:
        try:
            self.classes = self.api_client.get_classes()
            self.cb_class["values"] = [c["name"] for c in self.classes]
            self.cb_class.set("")
            self.current_class = None
            self.subjects = []
            self.cb_subject["values"] = []
            self.cb_subject.set("")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _on_class_selected(self, event=None) -> None:
        idx = self.cb_class.current()
        if idx < 0 or idx >= len(self.classes):
            return
        self.current_class = self.classes[idx]
        try:
            self.subjects = self.api_client.get_subjects(self.current_class["id"])
            self.cb_subject["values"] = [s["name"] for s in self.subjects]
            self.cb_subject.set("")
            self.current_subject = None
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _on_subject_selected(self, event=None) -> None:
        idx = self.cb_subject.current()
        if idx < 0 or idx >= len(self.subjects):
            return
        self.current_subject = self.subjects[idx]
        self._refresh_queue()

    def _refresh_queue(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.raw_text.delete("1.0", tk.END)

        if not self.current_subject:
            return

        try:
            self.review_items = self.api_client.get_review_queue(self.current_subject["id"])
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))
            return

        for item in self.review_items:
            self.tree.insert(
                "",
                tk.END,
                iid=str(item.get("submission_id")),
                values=(
                    item.get("submission_id"),
                    item.get("student_name", ""),
                    item.get("score", ""),
                    self._fmt(item.get("ocr_confidence")),
                    self._fmt(item.get("image_quality")),
                    item.get("review_reason", ""),
                    item.get("review_status", ""),
                ),
            )

    def _on_select(self, event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        submission_id = selection[0]
        item = next((i for i in self.review_items if str(i.get("submission_id")) == submission_id), None)
        if not item:
            return
        self.raw_text.delete("1.0", tk.END)
        text = self._clean_ocr_text(item.get("raw_text") or "")
        self.raw_text.insert(tk.END, text or "Aucun texte OCR.")

    def _mark_resolved(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        submission_id = int(selection[0])
        try:
            self.api_client.update_review_status(submission_id, {"review_status": "resolved"})
            self._refresh_queue()
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _fmt(self, value) -> str:
        if value is None:
            return "-"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

    def _clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""
        lines = [line for line in text.splitlines() if not line.strip().startswith("[INFO]")]
        return "\n".join(lines).strip()
