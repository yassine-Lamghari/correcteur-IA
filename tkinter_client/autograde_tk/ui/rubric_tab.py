import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk

from autograde_tk.ui.theme import get_theme


class RubricTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.classes = []
        self.subjects = []
        self.rubrics = []
        self.current_class = None
        self.current_subject = None
        self.current_rubric = None
        self._build_ui()
        self._load_classes()

    def _build_ui(self) -> None:
        theme = get_theme(self)

        top = ttk.Labelframe(self, text="Baremes", padding=10, bootstyle="info")
        top.pack(side=tk.TOP, fill="x", pady=(0, 10))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Classe:", font=theme.base_bold).grid(row=0, column=0, sticky="w")
        self.cb_class = ttk.Combobox(top, state="readonly", width=18, bootstyle="primary")
        self.cb_class.grid(row=0, column=1, sticky="w")
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)

        ttk.Label(top, text="Matiere:", font=theme.base_bold).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.cb_subject = ttk.Combobox(top, state="readonly", width=18, bootstyle="primary")
        self.cb_subject.grid(row=0, column=3, sticky="w")
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)

        ttk.Label(top, text="Bareme:", font=theme.base_bold).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.cb_rubric = ttk.Combobox(top, state="readonly", width=28, bootstyle="secondary")
        self.cb_rubric.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.cb_rubric.bind("<<ComboboxSelected>>", self._on_rubric_selected)

        btn_row = ttk.Frame(top)
        btn_row.grid(row=1, column=3, sticky="e", pady=(8, 0))
        ttk.Button(btn_row, text="Nouveau", command=self._new_rubric, bootstyle="secondary").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Sauver", command=self._save_rubric, bootstyle="success").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Activer", command=self._activate_rubric, bootstyle="success").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="Regrader", command=self._regrade, bootstyle="warning").pack(side=tk.LEFT)

        form = ttk.Labelframe(self, text="Details du bareme", padding=10, bootstyle="secondary")
        form.pack(side=tk.TOP, fill="x", pady=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Nom:", font=theme.base_bold).grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, bootstyle="primary").grid(row=0, column=1, sticky="ew")

        ttk.Label(form, text="Description:", font=theme.base_bold).grid(row=1, column=0, sticky="nw", pady=(6, 0))
        self.desc_text = tk.Text(form, height=3, wrap="word", font=theme.base)
        self.desc_text.grid(row=1, column=1, sticky="ew", pady=(6, 0))

        items_frame = ttk.Labelframe(self, text="Items (QID | type | points | reponse | mots-cles)", padding=10, bootstyle="secondary")
        items_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        items_frame.columnconfigure(0, weight=1)
        items_frame.rowconfigure(0, weight=1)

        self.items_text = tk.Text(items_frame, wrap="none", height=12, font=theme.mono)
        self.items_text.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.items_text.configure(yscrollcommand=sb.set)

        action_row = ttk.Frame(self)
        action_row.pack(side=tk.TOP, fill="x", pady=(8, 0))
        ttk.Button(action_row, text="Sauver", command=self._save_rubric, bootstyle="success").pack(side=tk.RIGHT)

    def _load_classes(self) -> None:
        try:
            self.classes = self.api_client.get_classes()
            self.cb_class["values"] = [c["name"] for c in self.classes]
            self.cb_class.set("")
            self.subjects = []
            self.cb_subject["values"] = []
            self.cb_subject.set("")
            self._refresh_rubrics([])
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
            self._refresh_rubrics([])
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _on_subject_selected(self, event=None) -> None:
        idx = self.cb_subject.current()
        if idx < 0 or idx >= len(self.subjects):
            return
        self.current_subject = self.subjects[idx]
        self._load_rubrics()

    def _load_rubrics(self) -> None:
        if not self.current_subject:
            return
        try:
            self.rubrics = self.api_client.get_rubrics(self.current_subject["id"])
            self._refresh_rubrics(self.rubrics)
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _refresh_rubrics(self, rubrics: list) -> None:
        self.cb_rubric["values"] = [r["name"] for r in rubrics]
        self.cb_rubric.set("")
        self.current_rubric = None
        self._clear_form()

    def _clear_form(self) -> None:
        self.name_var.set("")
        self.desc_text.delete("1.0", tk.END)
        self.items_text.delete("1.0", tk.END)

    def _on_rubric_selected(self, event=None) -> None:
        idx = self.cb_rubric.current()
        if idx < 0 or idx >= len(self.rubrics):
            return
        rubric = self.rubrics[idx]
        self.current_rubric = rubric
        self.name_var.set(rubric.get("name", ""))
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, rubric.get("description") or "")
        self.items_text.delete("1.0", tk.END)
        for item in rubric.get("items", []):
            keywords = ",".join(item.get("keywords") or [])
            line = f"{item.get('question_id','')} | {item.get('question_type','mcq')} | {item.get('max_points',0)} | {item.get('expected_answer','')} | {keywords}"
            self.items_text.insert(tk.END, line + "\n")

    def _new_rubric(self) -> None:
        self.current_rubric = None
        self.cb_rubric.set("")
        self._clear_form()

    def _parse_items(self) -> list:
        items = []
        raw = self.items_text.get("1.0", tk.END).strip()
        if not raw:
            return items

        for idx, line in enumerate(raw.splitlines()):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            qid = parts[0]
            qtype = parts[1] or "mcq"
            try:
                max_points = float(parts[2])
            except ValueError:
                max_points = 0.0
            expected = parts[3] if len(parts) > 3 else ""
            keywords = []
            if len(parts) > 4 and parts[4]:
                keywords = [k.strip() for k in parts[4].split(",") if k.strip()]

            items.append({
                "question_id": qid,
                "question_type": qtype,
                "max_points": max_points,
                "expected_answer": expected or None,
                "keywords": keywords,
                "order_index": idx,
            })
        return items

    def _save_rubric(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Attention", "Selectionnez une matiere.")
            return

        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Attention", "Nom du bareme requis.")
            return

        items = self._parse_items()
        payload = {
            "subject_id": self.current_subject["id"],
            "name": name,
            "description": self.desc_text.get("1.0", tk.END).strip() or None,
            "items": items,
        }

        try:
            if self.current_rubric is None:
                rubric = self.api_client.create_rubric(payload)
            else:
                rubric_id = self.current_rubric["id"]
                self.api_client.update_rubric(rubric_id, {
                    "name": name,
                    "description": payload["description"],
                })
                rubric = self.api_client.replace_rubric_items(rubric_id, items)
            self._load_rubrics()
            messagebox.showinfo("Succes", "Bareme enregistre.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _activate_rubric(self) -> None:
        if not self.current_rubric:
            messagebox.showwarning("Attention", "Selectionnez un bareme.")
            return
        try:
            self.api_client.activate_rubric(self.current_rubric["id"])
            messagebox.showinfo("Succes", "Bareme active.")
            self._load_rubrics()
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _regrade(self) -> None:
        if not self.current_rubric or not self.current_subject:
            messagebox.showwarning("Attention", "Selectionnez un bareme et une matiere.")
            return

        if not messagebox.askyesno("Regrader", "Regrader toutes les copies de cette matiere ?"):
            return

        try:
            self.api_client.regrade_submissions({
                "rubric_id": self.current_rubric["id"],
                "subject_id": self.current_subject["id"],
            })
            messagebox.showinfo("Succes", "Regrading termine.")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))
