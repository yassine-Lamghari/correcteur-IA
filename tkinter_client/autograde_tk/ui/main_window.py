from __future__ import annotations

import base64
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests

from autograde_tk.api_client import AutoGradeApiClient
from autograde_tk.ui.analysis_tab import AnalysisTab
from autograde_tk.ui.course_tab import CourseTab
from autograde_tk.ui.exam_tab import ExamTab
from autograde_tk.ui.review_tab import ReviewTab
from autograde_tk.ui.rubric_tab import RubricTab
from autograde_tk.ui.students_tab import StudentsTab
from autograde_tk.ui.tdtp_tab import TDTPTab
from autograde_tk.ui.theme import apply_theme, get_theme

class MainWindow(ttk.Frame):
    def __init__(self, master: ttk.Window, client: AutoGradeApiClient) -> None:
        super().__init__(master, padding=20)
        self.client = client
        self.ui_theme = get_theme(self)
        self.selected_image_b64 = ""

        # Session State
        self.current_class = None
        self.current_subject = None
        self.current_rubric = None
        self.rubrics = []

        self.task = tk.StringVar(value="Text")
        self.student_name = tk.StringVar(value="Élève Anonyme")
        self.student_answer = tk.StringVar(value="")
        self.use_llm = tk.BooleanVar(value=True)
        self.selected_images = []
        self.batch_results = []
        self.batch_results_by_row_id = {}
        self._validate_job = None

        self.grid(sticky="nsew", row=0, column=0)
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self._build_auth_ui()

    def _build_auth_ui(self) -> None:
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        theme = get_theme(self)

        # Cadre global centré (type carte)
        auth_container = ttk.Frame(self, padding=32, style="Card.TFrame")
        auth_container.place(relx=0.5, rely=0.5, anchor="center")

        title_frame = ttk.Frame(auth_container, style="Card.TFrame")
        title_frame.pack(fill="x", pady=(0, 30))
        
        icon_label = ttk.Label(title_frame, text="🔒", font=theme.title)
        icon_label.pack(side="top")
        
        title = ttk.Label(title_frame, text="AutoGrade OCR", font=theme.title, bootstyle="primary")
        title.pack(side="top")
        
        subtitle = ttk.Label(title_frame, text="Veuillez vous authentifier pour continuer", style="Muted.TLabel")
        subtitle.pack(side="top", pady=(5, 0))

        notebook = ttk.Notebook(auth_container, bootstyle="primary")
        notebook.pack(fill="both", expand=True)

        # --- Login Tab ---
        login_tab = ttk.Frame(notebook, padding=24)
        notebook.add(login_tab, text=" Connexion ")

        ttk.Label(login_tab, text="Nom d'utilisateur", font=theme.base_bold).pack(anchor="w", pady=(0, 5))
        self.login_user_var = tk.StringVar()
        ttk.Entry(login_tab, textvariable=self.login_user_var, bootstyle="primary", font=theme.base).pack(fill="x", pady=(0, 15), ipady=5)

        ttk.Label(login_tab, text="Mot de passe", font=theme.base_bold).pack(anchor="w", pady=(0, 5))
        self.login_pass_var = tk.StringVar()
        ttk.Entry(login_tab, textvariable=self.login_pass_var, show="*", bootstyle="primary", font=theme.base).pack(fill="x", pady=(0, 25), ipady=5)

        ttk.Button(login_tab, text="SE CONNECTER", command=self._do_login, bootstyle="success", cursor="hand2").pack(fill="x", ipady=5)

        # --- Register Tab ---
        register_tab = ttk.Frame(notebook, padding=24)
        notebook.add(register_tab, text=" Inscription ")

        ttk.Label(register_tab, text="Nom d'utilisateur", font=theme.base_bold).pack(anchor="w", pady=(0, 5))
        self.reg_user_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_user_var, bootstyle="info", font=theme.base).pack(fill="x", pady=(0, 10), ipady=4)

        ttk.Label(register_tab, text="Email", font=theme.base_bold).pack(anchor="w", pady=(0, 5))
        self.reg_email_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_email_var, bootstyle="info", font=theme.base).pack(fill="x", pady=(0, 10), ipady=4)

        ttk.Label(register_tab, text="Mot de passe", font=theme.base_bold).pack(anchor="w", pady=(0, 5))
        self.reg_pass_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_pass_var, show="*", bootstyle="info", font=theme.base).pack(fill="x", pady=(0, 25), ipady=4)

        ttk.Button(register_tab, text="S'INSCRIRE", command=self._do_register, bootstyle="info-outline", cursor="hand2").pack(fill="x", ipady=5)

    def _do_login(self) -> None:
        user = self.login_user_var.get().strip()
        pwd = self.login_pass_var.get()
        if not user or not pwd:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")
            return
        try:
            self.client.login(user, pwd)
            messagebox.showinfo("Succès", "Connexion réussie !")
            self._show_app_ui()
        except requests.exceptions.RequestException as e:
            msg = str(e)
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                msg = "Identifiants incorrects."
            messagebox.showerror("Erreur", msg)

    def _do_register(self) -> None:
        user = self.reg_user_var.get().strip()
        email = self.reg_email_var.get().strip()
        pwd = self.reg_pass_var.get()
        if not user or not email or not pwd:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")
            return
            
        try:
            self.client.register(user, email, pwd)
            messagebox.showinfo("Succès", "Inscription réussie ! Connexion automatique en cours...")
            self.client.login(user, pwd)
            self._show_app_ui()
        except requests.exceptions.RequestException as e:
            msg = str(e)
            if hasattr(e, 'response') and e.response is not None and e.response.status_code in [400, 422]:
                if e.response.status_code == 422:
                    msg = "Format de données invalide (vérifiez l'email et un mot de passe de >6 min)."
                else:
                    msg = e.response.json().get("detail", msg)
            messagebox.showerror("Erreur", msg)

    def _show_app_ui(self) -> None:
        # Clear auth widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        # Reset geometry behavior
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Notebook
        self.rowconfigure(2, weight=0)  # Log window
        self.rowconfigure(3, weight=0)  # Status bar

        self._build_header()
        self._build_app_ui()
        self._build_status_bar()
        self._apply_theme(self.theme_var.get())
        self._load_classes()

    def _build_header(self) -> None:
        theme = get_theme(self)
        header_frame = ttk.Frame(self, padding=(14, 10), bootstyle="secondary")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        user_label = ttk.Label(
            header_frame,
            text=f"👤 Bienvenue, {self.client.username or 'Utilisateur'}",
            font=theme.base_bold,
        )
        user_label.grid(row=0, column=0, sticky="w")

        self.dark_themes = {"cyborg", "darkly", "solar", "superhero", "vapor"}
        self.available_themes = [
            "litera",
            "flatly",
            "cosmo",
            "minty",
            "journal",
            "darkly",
            "cyborg",
            "superhero",
            "solar",
        ]
        current_theme = self.master.style.theme_use()
        if current_theme not in self.available_themes:
            self.available_themes.insert(0, current_theme)

        theme_label = ttk.Label(header_frame, text="Thème:", font=theme.base_bold)
        theme_label.grid(row=0, column=2, sticky="e", padx=(0, 6))

        self.theme_var = tk.StringVar(value=current_theme)
        self.theme_cb = ttk.Combobox(
            header_frame,
            textvariable=self.theme_var,
            values=self.available_themes,
            state="readonly",
            width=12,
            bootstyle="info",
        )
        self.theme_cb.grid(row=0, column=3, sticky="e")
        self.theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)
        self._apply_theme(current_theme)

    def _on_theme_change(self, event=None) -> None:
        theme_name = (self.theme_var.get() or "").strip()
        if not theme_name:
            return
        self._apply_theme(theme_name)

    def _apply_theme(self, theme_name: str) -> None:
        try:
            self.master.style.theme_use(theme_name)
        except Exception:
            return

        self.ui_theme = apply_theme(self.master)

        is_dark = theme_name in self.dark_themes
        if is_dark:
            log_bg = "#0b1220"
            log_fg = "#b3f5cf"
            extract_bg = "#0f172a"
            extract_fg = "#e5e7eb"
        else:
            theme = get_theme(self)
            log_bg = theme.log_bg
            log_fg = theme.log_fg
            extract_bg = theme.text_bg
            extract_fg = theme.text_fg

        if hasattr(self, "output"):
            self.output.config(bg=log_bg, fg=log_fg)
        if hasattr(self, "extraction_text"):
            self.extraction_text.config(bg=extract_bg, fg=extract_fg)

    def _build_app_ui(self) -> None:
        notebook = ttk.Notebook(self, bootstyle="primary")
        notebook.grid(row=1, column=0, sticky="nsew")

        self.course_tab = CourseTab(notebook, self.client)
        notebook.add(self.course_tab, text=" 📚 Génération de Cours (Gemini) ")

        self.tdtp_tab = TDTPTab(notebook, self.client)
        notebook.add(self.tdtp_tab, text=" TD/TP ")

        self.students_tab = StudentsTab(notebook, self.client)
        notebook.add(self.students_tab, text=" 👥 Etudiants ")

        self.rubric_tab = RubricTab(notebook, self.client)
        notebook.add(self.rubric_tab, text=" 📏 Baremes ")

        self.review_tab = ReviewTab(notebook, self.client)
        notebook.add(self.review_tab, text=" 🔍 Verification ")

        corrector_tab = ttk.Frame(notebook, padding=10)
        notebook.add(corrector_tab, text=" ✅ Correcteur Automatique ")

        self.analysis_tab = AnalysisTab(notebook, self.client, get_batch_results=lambda: self.batch_results)
        notebook.add(self.analysis_tab, text=" 📊 Analyse ")

        self.exam_tab = ExamTab(notebook, self.client)
        notebook.add(self.exam_tab, text=" 📝 Générateur d'Examen ")

        self._build_corrector_ui(corrector_tab)

    def _build_status_bar(self) -> None:
        theme = get_theme(self)
        self.status_var = tk.StringVar(value="Prêt")
        self.status_frame = ttk.Frame(self, padding=(10, 6), bootstyle="light")
        self.status_frame.grid(row=3, column=0, sticky="ew")
        self.status_frame.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, style="Muted.TLabel", font=theme.small)
        self.status_label.grid(row=0, column=0, sticky="w")

    def _build_corrector_ui(self, parent: ttk.Frame) -> None:
        theme = get_theme(self)
        parent.columnconfigure(0, weight=1)
        # --- Top Bar: Hierarchical Selectors ---
        top_frame = ttk.Labelframe(parent, text="Contexte Pédagogique", padding=10, bootstyle="info")
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))

        ttk.Label(top_frame, text="Filière (Classe):", font=theme.base_bold).grid(row=0, column=0, padx=5, sticky="e")
        self.cb_class = ttk.Combobox(top_frame, state="readonly", width=15, bootstyle="primary")
        self.cb_class.grid(row=0, column=1, padx=5)
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)
        
        self.btn_add_class = ttk.Button(top_frame, text="+", width=2, command=self._add_class, bootstyle="outline-primary")
        self.btn_add_class.grid(row=0, column=2, padx=5)

        ttk.Label(top_frame, text="Matière:", font=theme.base_bold).grid(row=0, column=3, padx=10, sticky="e")
        self.cb_subject = ttk.Combobox(top_frame, state="readonly", width=15, bootstyle="primary")
        self.cb_subject.grid(row=0, column=4, padx=5)
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)
        
        self.btn_add_subject = ttk.Button(top_frame, text="+", width=2, command=self._add_subject, bootstyle="outline-primary")
        self.btn_add_subject.grid(row=0, column=5, padx=5)

        ttk.Label(top_frame, text="Bareme:", font=theme.base_bold).grid(row=0, column=6, padx=10, sticky="e")
        self.cb_rubric = ttk.Combobox(top_frame, state="readonly", width=18, bootstyle="secondary")
        self.cb_rubric.grid(row=0, column=7, padx=5)
        self.cb_rubric.bind("<<ComboboxSelected>>", self._on_rubric_selected)

        # --- Batch Grading Configuration ---
        batch_frame = ttk.Labelframe(parent, text="Configuration Batch Grading", padding=10, bootstyle="primary")
        batch_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 5))

        top_inner = ttk.Frame(batch_frame)
        top_inner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        self.btn_select_images = ttk.Button(top_inner, text="Images de l'Exam", command=self._select_images, bootstyle="warning")
        self.btn_select_images.grid(row=0, column=0, sticky="w", padx=5)
        self.lbl_images = ttk.Label(top_inner, text="0", font=theme.small)
        self.lbl_images.grid(row=0, column=1, sticky="w", padx=10)

        ans_frame = ttk.Labelframe(batch_frame, text="Réponses", padding=5, bootstyle="secondary")
        ans_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=10)
        
        self.correct_answers_text = tk.Text(ans_frame, height=3, width=30, wrap="word", font=theme.mono)
        self.correct_answers_text.grid(row=0, column=0, sticky="ew")
        self.correct_answers_text.insert(tk.END, "1 A\n2 B\n3 C\n4 D")
        self.correct_answers_text.tag_configure("error", background="#ffe0e0")
        self.correct_answers_text.bind("<KeyRelease>", self._on_correct_answers_key)

        self.btn_run_batch = ttk.Button(batch_frame, text="Lancer Batch", command=self._run_batch, bootstyle="success")
        self.btn_run_batch.grid(row=1, column=0, columnspan=2, pady=5)

        self.batch_progress = ttk.Progressbar(batch_frame, mode="indeterminate", bootstyle="success-striped")
        self.batch_progress.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
        self.batch_progress.grid_remove()

        # --- Data Grid for Results ---
        grid_frame = ttk.Labelframe(parent, text="Résultats de Correction", padding=10, bootstyle="secondary")
        grid_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        parent.rowconfigure(2, weight=1)

        filter_frame = ttk.Frame(grid_frame)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        filter_frame.columnconfigure(1, weight=1)
        ttk.Label(filter_frame, text="Filtrer:", font=theme.small).grid(row=0, column=0, sticky="w")
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, bootstyle="info")
        self.filter_entry.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(filter_frame, text="Effacer", command=self._clear_filter, bootstyle="outline-secondary").grid(row=0, column=2)
        self.filter_var.trace_add("write", lambda *_: self._refresh_tree())
        
        columns = ("ID", "Nom", "Note", "Qualite", "A verifier", "Réponses", "Classe", "Matière")
        self.tree = ttk.Treeview(grid_frame, columns=columns, show="headings", height=6, bootstyle="info")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, minwidth=80, width=120, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Text box for OCR extraction display
        self.extraction_text = tk.Text(
            grid_frame,
            width=30,
            height=6,
            wrap="word",
            bg=theme.text_bg,
            fg=theme.text_fg,
            font=theme.mono,
        )
        self.extraction_text.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        grid_frame.columnconfigure(0, weight=3)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(1, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        btn_action_frame = ttk.Frame(grid_frame)
        btn_action_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=10)
        self.btn_save_notes = ttk.Button(btn_action_frame, text="Enregistrer les Notes !", command=self._save_submission, bootstyle="success")
        self.btn_save_notes.grid(row=0, column=0, padx=5)

        # --- Export Section ---
        export_frame = ttk.Frame(parent)
        export_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        self.btn_export_excel = ttk.Button(export_frame, text="Exporter les notes en Excel", command=self._export_excel, bootstyle="outline-success")
        self.btn_export_excel.grid(row=0, column=0, sticky="w", padx=5)

        # --- Log Output ---
        self.output = tk.Text(self, height=8, wrap="word", bg=theme.log_bg, fg=theme.log_fg, font=theme.mono)
        self.output.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(15, 0))
        self.output.tag_configure("info", foreground="#93c5fd")
        self.output.tag_configure("warn", foreground="#fbbf24")
        self.output.tag_configure("error", foreground="#f87171")
        self.output.tag_configure("success", foreground="#34d399")

        parent.rowconfigure(2, weight=1)

        # La configuration globale prend row=2 pour le Log Output, et l'onglet Correcteur se met en row=1
        self.rowconfigure(2, weight=0)
        self.rowconfigure(1, weight=1)


    # --- Hierarchy Methods ---
    def _load_classes(self):
        try:
            self.classes = self.client.get_classes()
            self.cb_class["values"] = [c["name"] for c in self.classes]
            self.cb_class.set('')
            self.cb_subject.set('')
            self.current_class = None
            self.current_subject = None
        except Exception as e:
            self._append_output(f"Error loading classes: {e}")

    def _on_class_selected(self, event):
        idx = self.cb_class.current()
        if idx >= 0:
            self.current_class = self.classes[idx]
            self._load_subjects()

    def _load_subjects(self):
        if not self.current_class: return
        try:
            self.subjects = self.client.get_subjects(self.current_class["id"])
            self.cb_subject["values"] = [s["name"] for s in self.subjects]
            self.cb_subject.set('')
            self.current_subject = None
            self._load_rubrics()
        except Exception as e:
            self._append_output(f"Error loading subjects: {e}")

    def _on_subject_selected(self, event):
        idx = self.cb_subject.current()
        if idx >= 0:
            self.current_subject = self.subjects[idx]
            self._load_rubrics()

    def _load_rubrics(self) -> None:
        if not self.current_subject:
            if hasattr(self, "cb_rubric"):
                self.cb_rubric["values"] = []
                self.cb_rubric.set("")
            self.current_rubric = None
            self.rubrics = []
            return

        try:
            self.rubrics = self.client.get_rubrics(self.current_subject["id"])
            self.cb_rubric["values"] = [r.get("name", "") for r in self.rubrics]
            active = next((r for r in self.rubrics if r.get("is_active")), None)
            if active:
                self.current_rubric = active
                self.cb_rubric.set(active.get("name", ""))
            else:
                self.current_rubric = None
                self.cb_rubric.set("")
        except Exception as e:
            self._append_output(f"Error loading rubrics: {e}")

    def _on_rubric_selected(self, event=None) -> None:
        idx = self.cb_rubric.current()
        if idx < 0 or idx >= len(self.rubrics):
            self.current_rubric = None
            return
        self.current_rubric = self.rubrics[idx]

    def _add_class(self):
        name = simpledialog.askstring("Nouvelle Filière", "Nom de la filière/classe (ex: Math 101):")
        if name:
            self.client.create_class(name)
            self._load_classes()

    def _add_subject(self):
        if not self.current_class:
            messagebox.showwarning("Attention", "Sélectionnez une classe d'abord.")
            return
        name = simpledialog.askstring("Nouvelle Matière", "Nom du modèle/matière:")
        if name:
            self.client.create_subject(name, self.current_class["id"])
            self._load_subjects()

    # --- Batch Grading Actions ---
    def _select_images(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Sélectionner l'image (ou les images) de l'examen",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp"), ("Tous les fichiers", "*.*")]
        )
        if file_paths:
            self.selected_images = list(file_paths)
            if len(self.selected_images) == 1:
                self.lbl_images.config(text=f"1 image sélectionnée: {os.path.basename(self.selected_images[0])}")
            else:
                self.lbl_images.config(text=f"{len(self.selected_images)} images sélectionnées")
            self._append_output(f"{len(self.selected_images)} image(s) sélectionnée(s)", level="info")

    def _on_correct_answers_key(self, event=None) -> None:
        if self._validate_job:
            self.after_cancel(self._validate_job)
        self._validate_job = self.after(250, self._validate_correct_answers)

    def _validate_correct_answers(self) -> list:
        self.correct_answers_text.tag_remove("error", "1.0", tk.END)
        text = self.correct_answers_text.get("1.0", tk.END).strip()
        errors = []
        if not text:
            return errors

        pattern = re.compile(r"^(\d+)\s+([A-Da-d]|[1-4])$")
        for idx, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            if not pattern.match(line.strip()):
                errors.append(idx)
                self.correct_answers_text.tag_add("error", f"{idx}.0", f"{idx}.end")

        if errors:
            self._set_status(f"{len(errors)} ligne(s) invalides dans les réponses", level="warn")
        return errors

    def _parse_correct_answers(self) -> tuple:
        text = self.correct_answers_text.get("1.0", tk.END).strip()
        errors = self._validate_correct_answers()
        answers = {}
        if not text:
            return answers, errors

        pattern = re.compile(r"^(\d+)\s+([A-Da-d]|[1-4])$")
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            q_id, ans = match.groups()
            answers[q_id] = ans.upper()
        return answers, errors

    def _run_batch(self) -> None:
        if not self.selected_images:
            messagebox.showwarning("Erreur", "Veuillez sélectionner au moins une image.")
            return

        if not self.current_subject:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une matière (cadre haut).")
            return

        correct_answers, errors = self._parse_correct_answers()
        if errors:
            messagebox.showwarning("Erreur", "Corrigez les lignes invalides dans les réponses.")
            return
        if not correct_answers:
            messagebox.showwarning("Erreur", "Veuillez entrer les réponses correctes.")
            return

        image_paths = list(self.selected_images)
        self._set_busy(True, f"Traitement de {len(image_paths)} copie(s)...")
        self._append_output(f"Lancement du Batch Grading pour {len(image_paths)} copie(s)...", level="info")

        def task() -> None:
            try:
                images_b64, filenames = self._encode_images(image_paths)
                if not images_b64:
                    raise ValueError("Aucune image valide trouvée.")
                rubric_id = self.current_rubric["id"] if self.current_rubric else None
                results = self.client.batch_grade(correct_answers, images_b64, rubric_id=rubric_id)
                self.after(0, lambda: self._on_batch_success(results, filenames))
            except Exception as exc:
                self.after(0, lambda err=exc: self._on_batch_error(err))

        threading.Thread(target=task, daemon=True).start()

    def _encode_images(self, image_paths: list) -> tuple:
        images_b64 = []
        filenames = []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        for path in image_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext and ext not in valid_exts:
                continue
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                images_b64.append(b64)
                filenames.append(os.path.basename(path))
        return images_b64, filenames

    def _on_batch_success(self, results: list, filenames: list) -> None:
        self._set_busy(False, "Batch terminé")
        self._append_output("Batch terminé.", level="success")

        self.batch_results = []
        self.batch_results_by_row_id = {}

        for i, res in enumerate(results):
            student_id = res.get("student_id", "Unknown")
            awarded = res.get("score", 0)
            answers = res.get("answers", {})
            answers_str = ", ".join([f"{k}: {v}" for k, v in answers.items()])
            raw_text = res.get("raw_text", "Aucun texte extrait disponible.")
            ocr_confidence = res.get("ocr_confidence")
            image_quality = res.get("image_quality")
            needs_review = bool(res.get("needs_review"))
            review_reason = res.get("review_reason")
            score_display = f"{awarded:.2f} / 20"
            quality_display = f"{image_quality:.2f}" if image_quality is not None else "-"
            review_display = "Oui" if needs_review else "Non"
            row_id = f"{student_id}-{i}"

            item = {
                "row_id": row_id,
                "student_id": student_id,
                "student_name": f"Élève_{student_id}",
                "score": awarded,
                "score_display": score_display,
                "ocr_confidence": ocr_confidence,
                "image_quality": image_quality,
                "needs_review": needs_review,
                "review_reason": review_reason,
                "quality_display": quality_display,
                "review_display": review_display,
                "answers_str": answers_str,
                "answers": answers,
                "feedback": "Batch graded",
                "filename": filenames[i] if i < len(filenames) else "",
                "raw_text": raw_text,
                "class_name": self.current_class["name"] if self.current_class else "-",
                "subject_name": self.current_subject["name"] if self.current_subject else "-",
            }
            self.batch_results.append(item)
            self.batch_results_by_row_id[row_id] = item

        self._refresh_tree()
        if hasattr(self, "analysis_tab"):
            self.analysis_tab.refresh_from_batch()

    def _on_batch_error(self, exc: Exception) -> None:
        self._set_busy(False, "Échec du batch")
        self._append_output(str(exc), level="error")
        messagebox.showerror("Erreur Batch", str(exc))

    def _on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item = self.batch_results_by_row_id.get(item_id)
        if not item:
            return
        self.extraction_text.delete("1.0", tk.END)
        text = item.get("raw_text") or "Aucun texte extrait."
        self.extraction_text.insert(tk.END, text)

    def _on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        column = self.tree.identify_column(event.x)
        if not column:
            return

        col_idx = int(column.replace("#", "")) - 1
        col_name = self.tree["columns"][col_idx]
        if col_name not in {"Nom", "Note"}:
            return

        self._edit_tree_cell(item_id, column, col_name)

    def _edit_tree_cell(self, item_id: str, column: str, col_name: str) -> None:
        bbox = self.tree.bbox(item_id, column)
        if not bbox:
            return
        x, y, width, height = bbox
        current_value = self.tree.set(item_id, col_name)

        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def save(event=None) -> None:
            new_val = entry.get().strip()
            if col_name == "Note":
                score = self._parse_score_value(new_val)
                if score is None or score < 0 or score > 20:
                    messagebox.showwarning("Note Invalide", "La note doit être comprise entre 0 et 20.")
                    entry.focus_set()
                    return
                display = f"{score:.2f} / 20"
                self.tree.set(item_id, col_name, display)
                item = self.batch_results_by_row_id.get(item_id)
                if item:
                    item["score"] = score
                    item["score_display"] = display
            else:
                if not new_val:
                    messagebox.showwarning("Nom invalide", "Le nom ne peut pas être vide.")
                    entry.focus_set()
                    return
                self.tree.set(item_id, col_name, new_val)
                item = self.batch_results_by_row_id.get(item_id)
                if item:
                    item["student_name"] = new_val

            entry.destroy()
            if (self.filter_var.get() or "").strip():
                self._refresh_tree()

        def cancel(event=None) -> None:
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", save)

    def _parse_score_value(self, value: str) -> float | None:
        if value is None:
            return None
        cleaned = value.replace(",", ".").split()[0]
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _clear_filter(self) -> None:
        self.filter_var.set("")

    def _refresh_tree(self) -> None:
        query = (self.filter_var.get() or "").strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.batch_results:
            haystack = " ".join(
                [
                    str(item.get("student_id", "")),
                    item.get("student_name", ""),
                    item.get("filename", ""),
                    item.get("answers_str", ""),
                    item.get("class_name", ""),
                    item.get("subject_name", ""),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            self.tree.insert(
                "",
                tk.END,
                iid=item["row_id"],
                values=(
                    item.get("student_id", ""),
                    item.get("student_name", ""),
                    item.get("score_display", ""),
                    item.get("quality_display", ""),
                    item.get("review_display", ""),
                    item.get("answers_str", ""),
                    item.get("class_name", "-"),
                    item.get("subject_name", "-"),
                ),
            )

    def _sort_tree(self, col: str, reverse: bool) -> None:
        rows = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        if col == "Note":
            rows.sort(
                key=lambda t: self._parse_score_value(t[0]) if self._parse_score_value(t[0]) is not None else -1,
                reverse=reverse,
            )
        elif col == "Qualite":
            def _quality(value: str) -> float:
                try:
                    return float(value)
                except ValueError:
                    return -1

            rows.sort(key=lambda t: _quality(t[0]), reverse=reverse)
        elif col == "ID":
            def _id_key(value: str) -> int:
                try:
                    return int(value)
                except ValueError:
                    return 0

            rows.sort(key=lambda t: _id_key(t[0]), reverse=reverse)
        else:
            rows.sort(key=lambda t: (t[0] or "").lower(), reverse=reverse)

        for index, (_, k) in enumerate(rows):
            self.tree.move(k, "", index)

        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    def _save_submission(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une matière.")
            return
            
        if not hasattr(self, "batch_results") or not self.batch_results:
            messagebox.showwarning("Erreur", "Aucune correction prête à enregistrer.")
            return
            
        try:
            for item in self.tree.get_children():
                vals = self.tree.item(item, "values")
                item_obj = self.batch_results_by_row_id.get(item) if hasattr(self, "batch_results_by_row_id") else None
                student_id = vals[0]
                student_name = vals[1]
                score = float(str(vals[2]).replace(" / 20", ""))
                
                self.client.create_submission(
                    student_name=student_name,
                    score=score,
                    feedback="Batch",
                    subject_id=self.current_subject["id"],
                    student_id=item_obj.get("student_id") if item_obj else None,
                    answers=item_obj.get("answers") if item_obj else None,
                    ocr_confidence=item_obj.get("ocr_confidence") if item_obj else None,
                    image_quality=item_obj.get("image_quality") if item_obj else None,
                    needs_review=item_obj.get("needs_review") if item_obj else None,
                    review_reason=item_obj.get("review_reason") if item_obj else None,
                    raw_text=item_obj.get("raw_text") if item_obj else None,
                )
            self._append_output(f"✅ {len(self.tree.get_children())} notes enregistrées.")
            self.batch_results = []
            
        except Exception as exc:
            messagebox.showerror("Erreur Sauvegarde", str(exc))

    def _export_excel(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Erreur", "Sélectionnez une matière pour l'export Excel.")
            return
        
        path = filedialog.asksaveasfilename(
            title="Exporter notes",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not path:
            return
            
        try:
            self._append_output("Génération Excel...")
            self.client.export_excel(self.current_subject["id"], path)
            self._append_output(f"Fichier exporté : {path}")
            messagebox.showinfo("Succès", "Rapport Excel généré avec succès!")
        except Exception as exc:
            messagebox.showerror("Erreur Export", str(exc))

    def _set_status(self, text: str, level: str = "info") -> None:
        if not hasattr(self, "status_var"):
            return
        level = (level or "info").lower()
        bootstyle_map = {
            "info": "secondary",
            "success": "success",
            "warn": "warning",
            "error": "danger",
        }
        self.status_var.set(text)
        if hasattr(self, "status_label"):
            self.status_label.configure(bootstyle=bootstyle_map.get(level, "secondary"))

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        if message:
            self._set_status(message, level="info")

        btn_state = tk.DISABLED if busy else tk.NORMAL
        combo_state = "disabled" if busy else "readonly"

        if hasattr(self, "btn_select_images"):
            self.btn_select_images.configure(state=btn_state)
        if hasattr(self, "btn_run_batch"):
            self.btn_run_batch.configure(state=btn_state)
        if hasattr(self, "btn_save_notes"):
            self.btn_save_notes.configure(state=btn_state)
        if hasattr(self, "btn_export_excel"):
            self.btn_export_excel.configure(state=btn_state)
        if hasattr(self, "btn_add_class"):
            self.btn_add_class.configure(state=btn_state)
        if hasattr(self, "btn_add_subject"):
            self.btn_add_subject.configure(state=btn_state)
        if hasattr(self, "cb_class"):
            self.cb_class.configure(state=combo_state)
        if hasattr(self, "cb_subject"):
            self.cb_subject.configure(state=combo_state)
        if hasattr(self, "cb_rubric"):
            self.cb_rubric.configure(state=combo_state)

        if hasattr(self, "batch_progress"):
            if busy:
                self.batch_progress.grid()
                self.batch_progress.start(12)
            else:
                self.batch_progress.stop()
                self.batch_progress.grid_remove()

    def _append_output(self, text: str, level: str = "info") -> None:
        level = (level or "info").lower()
        tag = level if level in {"info", "warn", "error", "success"} else "info"
        prefix = tag.upper()
        self.output.insert("end", f"[{prefix}] {text}\n", tag)
        self.output.see("end")
        self._set_status(text, level=tag)
