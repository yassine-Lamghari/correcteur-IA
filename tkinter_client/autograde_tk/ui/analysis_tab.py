import statistics
import threading
import tkinter as tk
import ttkbootstrap as ttk
from tkinter import filedialog, messagebox

from autograde_tk.ui.theme import get_theme


class AnalysisTab(ttk.Frame):
    def __init__(self, parent, api_client, get_batch_results):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.get_batch_results = get_batch_results

        self.classes = []
        self.subjects = []
        self.current_class = None
        self.current_subject = None

        self.source_var = tk.StringVar(value="db")
        self.status_var = tk.StringVar(value="Pret")

        self._build_ui()
        self._load_classes_async()

    def _build_ui(self) -> None:
        theme = get_theme(self)

        source_frame = ttk.Labelframe(self, text="Source & Contexte", padding=10, bootstyle="info")
        source_frame.pack(side=tk.TOP, fill="x", pady=(0, 10))
        source_frame.columnconfigure(1, weight=1)

        ttk.Label(source_frame, text="Source des notes:", font=theme.base_bold).grid(row=0, column=0, sticky="w")
        source_btns = ttk.Frame(source_frame)
        source_btns.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(
            source_btns,
            text="Notes enregistrees",
            value="db",
            variable=self.source_var,
            command=self._on_source_change,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(
            source_btns,
            text="Batch en cours",
            value="batch",
            variable=self.source_var,
            command=self._on_source_change,
        ).pack(side=tk.LEFT)

        ttk.Label(source_frame, text="Classe:", font=theme.base_bold).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.cb_class = ttk.Combobox(source_frame, state="readonly", width=18, bootstyle="primary")
        self.cb_class.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)

        ttk.Label(source_frame, text="Matiere:", font=theme.base_bold).grid(row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0))
        self.cb_subject = ttk.Combobox(source_frame, state="readonly", width=18, bootstyle="primary")
        self.cb_subject.grid(row=1, column=3, sticky="w", pady=(8, 0))
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)

        self.btn_refresh = ttk.Button(
            source_frame,
            text="Rafraichir",
            command=self._refresh_data,
            bootstyle="success",
        )
        self.btn_refresh.grid(row=0, column=3, sticky="e")

        export_row = ttk.Frame(source_frame)
        export_row.grid(row=0, column=4, sticky="e")
        ttk.Button(export_row, text="Exporter PDF", command=self._export_pdf, bootstyle="outline-primary").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(export_row, text="Exporter Excel", command=self._export_excel, bootstyle="outline-success").pack(
            side=tk.LEFT
        )

        summary_frame = ttk.Labelframe(self, text="Resume Statistique", padding=10, bootstyle="secondary")
        summary_frame.pack(side=tk.TOP, fill="x", pady=(0, 10))

        self.summary_vars = {}
        metrics = [
            ("count", "Effectif"),
            ("mean", "Moyenne"),
            ("median", "Mediane"),
            ("min", "Min"),
            ("max", "Max"),
            ("stdev", "Ecart-type"),
            ("pass_rate", "Taux de reussite"),
        ]
        for i, (key, label) in enumerate(metrics):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(summary_frame, text=f"{label}:", font=theme.base_bold).grid(row=row, column=col, sticky="w", padx=(0, 6), pady=4)
            var = tk.StringVar(value="-")
            self.summary_vars[key] = var
            ttk.Label(summary_frame, textvariable=var, font=theme.base).grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=4)

        dist_frame = ttk.Labelframe(self, text="Distribution (sur 20)", padding=10, bootstyle="secondary")
        dist_frame.pack(side=tk.TOP, fill="x", pady=(0, 10))
        dist_frame.columnconfigure(1, weight=1)

        self.distribution_rows = []
        bins = [
            ("0-4", 0, 4),
            ("4-8", 4, 8),
            ("8-12", 8, 12),
            ("12-16", 12, 16),
            ("16-20", 16, 20),
        ]
        for idx, (label, start, end) in enumerate(bins):
            ttk.Label(dist_frame, text=label, font=theme.base_bold).grid(row=idx, column=0, sticky="w", padx=(0, 10), pady=4)
            bar = ttk.Progressbar(dist_frame, maximum=100, bootstyle="info-striped")
            bar.grid(row=idx, column=1, sticky="ew", padx=(0, 10), pady=4)
            count_var = tk.StringVar(value="0 (0%)")
            ttk.Label(dist_frame, textvariable=count_var, font=theme.small).grid(row=idx, column=2, sticky="w")
            self.distribution_rows.append({"start": start, "end": end, "bar": bar, "count_var": count_var})

        rank_frame = ttk.Labelframe(self, text="Classement", padding=10, bootstyle="secondary")
        rank_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        rank_frame.columnconfigure(0, weight=1)
        rank_frame.columnconfigure(1, weight=1)

        left = ttk.Frame(rank_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ttk.Frame(rank_frame)
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(left, text="Top 5", font=theme.base_bold).pack(anchor="w")
        ttk.Label(right, text="Bottom 5", font=theme.base_bold).pack(anchor="w")

        columns = ("Nom", "Note")
        self.top_tree = ttk.Treeview(left, columns=columns, show="headings", height=6, bootstyle="success")
        self.bottom_tree = ttk.Treeview(right, columns=columns, show="headings", height=6, bootstyle="danger")
        for tree in (self.top_tree, self.bottom_tree):
            tree.heading("Nom", text="Nom")
            tree.heading("Note", text="Note")
            tree.column("Nom", width=180, anchor="w")
            tree.column("Note", width=80, anchor="center")

        self.top_tree.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.bottom_tree.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.status_label = ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", font=theme.small)
        self.status_label.pack(side=tk.BOTTOM, anchor="w", pady=(6, 0))

        self._on_source_change()

    def _on_source_change(self) -> None:
        source = (self.source_var.get() or "db").strip()
        is_db = source == "db"
        state = "readonly" if is_db else "disabled"
        self.cb_class.configure(state=state)
        self.cb_subject.configure(state=state)

    def _load_classes_async(self) -> None:
        def task():
            try:
                classes = self.api_client.get_classes()
                self.after(0, lambda: self._on_classes_loaded(classes))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Erreur chargement classes: {exc}", level="error"))

        threading.Thread(target=task, daemon=True).start()

    def _on_classes_loaded(self, classes: list) -> None:
        self.classes = classes or []
        self.cb_class["values"] = [c.get("name", "") for c in self.classes]
        self.cb_class.set("")
        self.subjects = []
        self.cb_subject["values"] = []
        self.cb_subject.set("")

    def _on_class_selected(self, event=None) -> None:
        idx = self.cb_class.current()
        if idx < 0 or idx >= len(self.classes):
            return
        self.current_class = self.classes[idx]
        self._load_subjects_async()

    def _load_subjects_async(self) -> None:
        if not self.current_class:
            return

        def task():
            try:
                subjects = self.api_client.get_subjects(self.current_class["id"])
                self.after(0, lambda: self._on_subjects_loaded(subjects))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Erreur chargement matieres: {exc}", level="error"))

        threading.Thread(target=task, daemon=True).start()

    def _on_subjects_loaded(self, subjects: list) -> None:
        self.subjects = subjects or []
        self.cb_subject["values"] = [s.get("name", "") for s in self.subjects]
        self.cb_subject.set("")
        self.current_subject = None

    def _on_subject_selected(self, event=None) -> None:
        idx = self.cb_subject.current()
        if idx < 0 or idx >= len(self.subjects):
            return
        self.current_subject = self.subjects[idx]

    def refresh_from_batch(self) -> None:
        if (self.source_var.get() or "db") != "batch":
            return
        self._load_batch_data()

    def _refresh_data(self) -> None:
        source = (self.source_var.get() or "db").strip()
        if source == "batch":
            self._load_batch_data()
            return

        if not self.current_subject:
            messagebox.showwarning("Attention", "Selectionnez une matiere pour analyser les notes.")
            return
        self._load_subject_data(self.current_subject["id"])

    def _load_batch_data(self) -> None:
        items = []
        if callable(self.get_batch_results):
            items = self.get_batch_results() or []
        self._update_analysis(self._normalize_entries(items), label="Batch en cours")

    def _load_subject_data(self, subject_id: int) -> None:
        self._set_status("Chargement des notes...", level="info")

        def task():
            try:
                submissions = self.api_client.get_submissions(subject_id)
                self.after(0, lambda: self._update_analysis(self._normalize_entries(submissions), label="Notes enregistrees"))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"Erreur chargement notes: {exc}", level="error"))

        threading.Thread(target=task, daemon=True).start()

    def _export_pdf(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Attention", "Selectionnez une matiere.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter le rapport PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="rapport_notes.pdf",
        )
        if not path:
            return
        try:
            self.api_client.export_report_pdf(self.current_subject["id"], path)
            messagebox.showinfo("Succes", f"Rapport PDF exporte: {path}")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _export_excel(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Attention", "Selectionnez une matiere.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter le rapport Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="rapport_notes.xlsx",
        )
        if not path:
            return
        try:
            self.api_client.export_excel(self.current_subject["id"], path)
            messagebox.showinfo("Succes", f"Rapport Excel exporte: {path}")
        except Exception as exc:
            messagebox.showerror("Erreur", str(exc))

    def _normalize_entries(self, items: list) -> list:
        entries = []
        for item in items or []:
            score = self._parse_score(item.get("score"))
            if score is None:
                continue
            name = item.get("student_name") or item.get("student_id") or "Eleve"
            entries.append({"name": name, "score": score})
        return entries

    def _parse_score(self, value) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", ".").split()[0]
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _update_analysis(self, entries: list, label: str) -> None:
        scores = [e["score"] for e in entries]
        if not scores:
            self._clear_analysis()
            self._set_status(f"Aucune note disponible ({label}).", level="warn")
            return

        stats = self._compute_stats(scores)
        self.summary_vars["count"].set(str(stats["count"]))
        self.summary_vars["mean"].set(self._fmt_score(stats["mean"]))
        self.summary_vars["median"].set(self._fmt_score(stats["median"]))
        self.summary_vars["min"].set(self._fmt_score(stats["min"]))
        self.summary_vars["max"].set(self._fmt_score(stats["max"]))
        self.summary_vars["stdev"].set(self._fmt_score(stats["stdev"]))
        self.summary_vars["pass_rate"].set(f"{stats['pass_rate']:.1f}%")

        self._update_distribution(scores)
        self._update_ranking(entries)
        self._set_status(f"Analyse mise a jour ({label}).", level="success")

    def _compute_stats(self, scores: list[float]) -> dict:
        count = len(scores)
        mean = sum(scores) / count if count else 0.0
        median = statistics.median(scores) if count else 0.0
        min_val = min(scores) if count else 0.0
        max_val = max(scores) if count else 0.0
        stdev = statistics.pstdev(scores) if count > 1 else 0.0
        pass_rate = (sum(1 for s in scores if s >= 10.0) / count * 100.0) if count else 0.0
        return {
            "count": count,
            "mean": mean,
            "median": median,
            "min": min_val,
            "max": max_val,
            "stdev": stdev,
            "pass_rate": pass_rate,
        }

    def _update_distribution(self, scores: list[float]) -> None:
        total = len(scores)
        counts = [0] * len(self.distribution_rows)
        for score in scores:
            idx = self._bin_index(score)
            counts[idx] += 1

        for row, count in zip(self.distribution_rows, counts):
            percent = (count / total * 100.0) if total else 0.0
            row["bar"].configure(value=percent)
            row["count_var"].set(f"{count} ({percent:.0f}%)")

    def _bin_index(self, score: float) -> int:
        if score < 4:
            return 0
        if score < 8:
            return 1
        if score < 12:
            return 2
        if score < 16:
            return 3
        return 4

    def _update_ranking(self, entries: list) -> None:
        for tree in (self.top_tree, self.bottom_tree):
            for item in tree.get_children():
                tree.delete(item)

        ordered = sorted(entries, key=lambda e: e["score"])
        bottom = ordered[:5]
        top = list(reversed(ordered[-5:]))

        for entry in top:
            self.top_tree.insert("", tk.END, values=(entry["name"], self._fmt_score(entry["score"])))
        for entry in bottom:
            self.bottom_tree.insert("", tk.END, values=(entry["name"], self._fmt_score(entry["score"])))

    def _clear_analysis(self) -> None:
        for var in self.summary_vars.values():
            var.set("-")
        for row in self.distribution_rows:
            row["bar"].configure(value=0)
            row["count_var"].set("0 (0%)")
        for tree in (self.top_tree, self.bottom_tree):
            for item in tree.get_children():
                tree.delete(item)

    def _fmt_score(self, value: float) -> str:
        return f"{value:.2f} / 20"

    def _set_status(self, text: str, level: str = "info") -> None:
        self.status_var.set(text)
        if not hasattr(self, "status_label"):
            return
        level = (level or "info").lower()
        style_map = {
            "info": "secondary",
            "success": "success",
            "warn": "warning",
            "error": "danger",
        }
        self.status_label.configure(bootstyle=style_map.get(level, "secondary"))
