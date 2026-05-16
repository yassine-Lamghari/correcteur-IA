import csv
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk

from autograde_tk.ui.theme import get_theme


class StudentsTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.classes = []
        self.current_class = None
        self._build_ui()
        self._load_classes()

    def _build_ui(self) -> None:
        theme = get_theme(self)

        top = ttk.Labelframe(self, text="Gestion des etudiants", padding=10, bootstyle="info")
        top.pack(side=tk.TOP, fill="x", pady=(0, 10))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Classe:", font=theme.base_bold).grid(row=0, column=0, sticky="w")
        self.cb_class = ttk.Combobox(top, state="readonly", width=20, bootstyle="primary")
        self.cb_class.grid(row=0, column=1, sticky="w")
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)

        ttk.Button(top, text="Rafraichir", command=self._load_classes, bootstyle="secondary").grid(
            row=0, column=2, padx=(10, 0)
        )

        btns = ttk.Frame(top)
        btns.grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="Importer CSV", command=self._import_csv, bootstyle="success").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(btns, text="Exporter CSV", command=self._export_csv, bootstyle="outline-primary").pack(
            side=tk.LEFT
        )

        grid = ttk.Labelframe(self, text="Liste des etudiants", padding=10, bootstyle="secondary")
        grid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)

        columns = ("Code", "Nom", "Email")
        self.tree = ttk.Treeview(grid, columns=columns, show="headings", height=12, bootstyle="info")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=200)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(grid, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _load_classes(self) -> None:
        try:
            self.classes = self.api_client.get_classes()
            self.cb_class["values"] = [c["name"] for c in self.classes]
            self.cb_class.set("")
            self.current_class = None
            self._refresh_students()
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _on_class_selected(self, event=None) -> None:
        idx = self.cb_class.current()
        if idx < 0 or idx >= len(self.classes):
            return
        self.current_class = self.classes[idx]
        self._refresh_students()

    def _refresh_students(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_class:
            return

        try:
            students = self.api_client.get_students(self.current_class["id"])
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))
            return

        for student in students:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    student.get("student_code", ""),
                    student.get("full_name", ""),
                    student.get("email", ""),
                ),
            )

    def _import_csv(self) -> None:
        if not self.current_class:
            messagebox.showwarning("Attention", "Selectionnez une classe d'abord.")
            return

        filepath = filedialog.askopenfilename(
            title="Importer une liste d'etudiants",
            filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")],
        )
        if not filepath:
            return

        students = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = (row.get("student_code") or row.get("code") or "").strip()
                    name = (row.get("full_name") or row.get("name") or row.get("nom") or "").strip()
                    email = (row.get("email") or "").strip()
                    if not code or not name:
                        continue
                    students.append({"student_code": code, "full_name": name, "email": email or None})
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de lire le CSV: {exc}")
            return

        if not students:
            messagebox.showwarning("Attention", "Aucun etudiant valide dans le CSV.")
            return

        try:
            self.api_client.create_students_bulk(self.current_class["id"], students)
            self._refresh_students()
            messagebox.showinfo("Succes", f"{len(students)} etudiants importes.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _export_csv(self) -> None:
        if not self.current_class:
            messagebox.showwarning("Attention", "Selectionnez une classe d'abord.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Exporter la liste des etudiants",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="etudiants.csv",
        )
        if not filepath:
            return

        try:
            self.api_client.export_students(self.current_class["id"], filepath)
            messagebox.showinfo("Succes", f"CSV exporte: {filepath}")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))
