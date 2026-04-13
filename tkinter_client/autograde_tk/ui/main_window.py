from __future__ import annotations

import base64
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests

from autograde_tk.api_client import AutoGradeApiClient
from autograde_tk.ui.exam_tab import ExamTab

class MainWindow(ttk.Frame):
    def __init__(self, master: ttk.Window, client: AutoGradeApiClient) -> None:
        super().__init__(master, padding=20)
        self.client = client
        self.selected_image_b64 = ""

        # Session State
        self.current_class = None
        self.current_subject = None

        self.task = tk.StringVar(value="Text")
        self.student_name = tk.StringVar(value="Élève Anonyme")
        self.student_answer = tk.StringVar(value="")
        self.use_llm = tk.BooleanVar(value=True)

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

        # Cadre global centré (type carte)
        auth_container = ttk.Frame(self, padding=40)
        auth_container.place(relx=0.5, rely=0.5, anchor="center")

        title_frame = ttk.Frame(auth_container)
        title_frame.pack(fill="x", pady=(0, 30))
        
        icon_label = ttk.Label(title_frame, text="🔒", font=("Helvetica", 32))
        icon_label.pack(side="top")
        
        title = ttk.Label(title_frame, text="AutoGrade OCR", font=("Segoe UI", 24, "bold"), bootstyle="primary")
        title.pack(side="top")
        
        subtitle = ttk.Label(title_frame, text="Veuillez vous authentifier pour continuer", font=("Segoe UI", 10), bootstyle="secondary")
        subtitle.pack(side="top", pady=(5, 0))

        notebook = ttk.Notebook(auth_container, bootstyle="info")
        notebook.pack(fill="both", expand=True)

        # --- Login Tab ---
        login_tab = ttk.Frame(notebook, padding=30)
        notebook.add(login_tab, text=" Connexion ")

        ttk.Label(login_tab, text="Nom d'utilisateur").pack(anchor="w", pady=(0, 5))
        self.login_user_var = tk.StringVar()
        ttk.Entry(login_tab, textvariable=self.login_user_var, bootstyle="primary", font=("Segoe UI", 11)).pack(fill="x", pady=(0, 15), ipady=5)

        ttk.Label(login_tab, text="Mot de passe").pack(anchor="w", pady=(0, 5))
        self.login_pass_var = tk.StringVar()
        ttk.Entry(login_tab, textvariable=self.login_pass_var, show="*", bootstyle="primary", font=("Segoe UI", 11)).pack(fill="x", pady=(0, 25), ipady=5)

        ttk.Button(login_tab, text="SE CONNECTER", command=self._do_login, bootstyle="success", cursor="hand2").pack(fill="x", ipady=5)

        # --- Register Tab ---
        register_tab = ttk.Frame(notebook, padding=30)
        notebook.add(register_tab, text=" Inscription ")

        ttk.Label(register_tab, text="Nom d'utilisateur").pack(anchor="w", pady=(0, 5))
        self.reg_user_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_user_var, bootstyle="info", font=("Segoe UI", 11)).pack(fill="x", pady=(0, 10), ipady=4)

        ttk.Label(register_tab, text="Email").pack(anchor="w", pady=(0, 5))
        self.reg_email_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_email_var, bootstyle="info", font=("Segoe UI", 11)).pack(fill="x", pady=(0, 10), ipady=4)

        ttk.Label(register_tab, text="Mot de passe").pack(anchor="w", pady=(0, 5))
        self.reg_pass_var = tk.StringVar()
        ttk.Entry(register_tab, textvariable=self.reg_pass_var, show="*", bootstyle="info", font=("Segoe UI", 11)).pack(fill="x", pady=(0, 25), ipady=4)

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

        self._build_header()
        self._build_app_ui()
        self._load_classes()

    def _build_header(self) -> None:
        header_frame = ttk.Frame(self, padding=10, bootstyle="secondary")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        user_label = ttk.Label(header_frame, text=f"👤 Bienvenue, {self.client.username or 'Utilisateur'}", font=("Segoe UI", 12, "bold"))
        user_label.grid(row=0, column=0, sticky="w")
        
        self.is_dark_theme = False
        self.theme_btn = ttk.Button(header_frame, text="🌙 Mode Sombre", command=self._toggle_theme, bootstyle="outline-dark")
        self.theme_btn.grid(row=0, column=2, sticky="e")
        
    def _toggle_theme(self) -> None:
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.master.style.theme_use("darkly")
            self.theme_btn.config(text="☀️ Mode Clair", bootstyle="outline-light")
            self.output.config(bg="#1e1e1e", fg="#00ff00")
            self.extraction_text.config(bg="#2d2d2d", fg="#cccccc")
        else:
            self.master.style.theme_use("litera")
            self.theme_btn.config(text="🌙 Mode Sombre", bootstyle="outline-dark")
            self.output.config(bg="#2b2b2b", fg="#00ff00") # Keeping logs dark
            self.extraction_text.config(bg="#fcfcfc", fg="#000000")

    def _build_app_ui(self) -> None:
        notebook = ttk.Notebook(self, bootstyle="info")
        notebook.grid(row=1, column=0, sticky="nsew")
        
        corrector_tab = ttk.Frame(notebook, padding=10)
        notebook.add(corrector_tab, text=" ✅ Correcteur Automatique ")
        
        self.exam_tab = ExamTab(notebook, self.client)
        notebook.add(self.exam_tab, text=" 📝 Générateur d'Examen ")

        self._build_corrector_ui(corrector_tab)

    def _build_corrector_ui(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        # --- Top Bar: Hierarchical Selectors ---
        top_frame = ttk.Labelframe(parent, text="Contexte Pédagogique", padding=10, bootstyle="info")
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))

        ttk.Label(top_frame, text="Filière (Classe):", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=5, sticky="e")
        self.cb_class = ttk.Combobox(top_frame, state="readonly", width=15, bootstyle="primary")
        self.cb_class.grid(row=0, column=1, padx=5)
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)
        
        ttk.Button(top_frame, text="+", width=2, command=self._add_class, bootstyle="outline-primary").grid(row=0, column=2, padx=5)

        ttk.Label(top_frame, text="Matière:", font=("Helvetica", 10, "bold")).grid(row=0, column=3, padx=10, sticky="e")
        self.cb_subject = ttk.Combobox(top_frame, state="readonly", width=15, bootstyle="primary")
        self.cb_subject.grid(row=0, column=4, padx=5)
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)
        
        ttk.Button(top_frame, text="+", width=2, command=self._add_subject, bootstyle="outline-primary").grid(row=0, column=5, padx=5)

        # --- Batch Grading Configuration ---
        batch_frame = ttk.Labelframe(parent, text="Configuration Batch Grading", padding=10, bootstyle="primary")
        batch_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 5))

        top_inner = ttk.Frame(batch_frame)
        top_inner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        ttk.Button(top_inner, text="Images de l'Exam", command=self._select_images, bootstyle="warning").grid(row=0, column=0, sticky="w", padx=5)
        self.lbl_images = ttk.Label(top_inner, text="0", font=("Helvetica", 10, "italic"))
        self.lbl_images.grid(row=0, column=1, sticky="w", padx=10)

        ans_frame = ttk.Labelframe(batch_frame, text="Réponses", padding=5, bootstyle="secondary")
        ans_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=10)
        
        self.correct_answers_text = tk.Text(ans_frame, height=3, width=30, wrap="word", font=("Courier", 10))
        self.correct_answers_text.grid(row=0, column=0, sticky="ew")
        self.correct_answers_text.insert(tk.END, "1 A\n2 B\n3 C\n4 D")

        ttk.Button(batch_frame, text="Lancer Batch", command=self._run_batch, bootstyle="success").grid(row=1, column=0, columnspan=2, pady=5)

        # --- Data Grid for Results ---
        grid_frame = ttk.Labelframe(parent, text="Résultats de Correction", padding=10, bootstyle="secondary")
        grid_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        parent.rowconfigure(2, weight=1)
        
        columns = ("ID", "Nom", "Note", "Réponses", "Classe", "Matière")
        self.tree = ttk.Treeview(grid_frame, columns=columns, show="headings", height=6, bootstyle="info")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, minwidth=80, width=120, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Text box for OCR extraction display
        self.extraction_text = tk.Text(grid_frame, width=30, height=6, wrap="word", bg="#fcfcfc", font=("Consolas", 9))
        self.extraction_text.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        grid_frame.columnconfigure(0, weight=3)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind("<Double-1>", self._on_double_click_tree)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        btn_action_frame = ttk.Frame(grid_frame)
        btn_action_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(btn_action_frame, text="Enregistrer les Notes !", command=self._save_submission, bootstyle="success").grid(row=0, column=0, padx=5)

        # --- Export Section ---
        export_frame = ttk.Frame(parent)
        export_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        ttk.Button(export_frame, text="Exporter les notes en Excel", command=self._export_excel, bootstyle="outline-success").grid(row=0, column=0, sticky="w", padx=5)

        # --- Log Output ---
        self.output = tk.Text(self, height=8, wrap="word", bg="#2b2b2b", fg="#00ff00", font=("Consolas", 10))
        self.output.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(15, 0))

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
        except Exception as e:
            self._append_output(f"Error loading subjects: {e}")

    def _on_subject_selected(self, event):
        idx = self.cb_subject.current()
        if idx >= 0:
            self.current_subject = self.subjects[idx]

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
            self._append_output(f"{len(self.selected_images)} image(s) sélectionnée(s)")

    def _parse_correct_answers(self) -> dict:
        text = self.correct_answers_text.get("1.0", tk.END).strip()
        answers = {}
        if not text:
            return answers
            
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                q_id, ans = parts
                answers[q_id] = ans
        return answers

    def _run_batch(self) -> None:
        if not hasattr(self, "selected_images") or not self.selected_images:
            messagebox.showwarning("Erreur", "Veuillez sélectionner au moins une image.")
            return

        if not self.current_subject:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une matière (cadre haut).")
            return
            
        correct_answers = self._parse_correct_answers()
        if not correct_answers:
            messagebox.showwarning("Erreur", "Veuillez entrer les réponses correctes.")
            return

        # Read images
        images_b64 = []
        filenames = []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        
        for path in self.selected_images:
            ext = os.path.splitext(path)[1].lower()
            if ext in valid_exts or not ext:  # Allow even if ext is missing but selected via dialog
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    images_b64.append(b64)
                    filenames.append(os.path.basename(path))
                    
        if not images_b64:
             messagebox.showinfo("Images Invalides", "Aucune image valide trouvée.")
             return

        self._append_output(f"Lancement du Batch Grading pour {len(images_b64)} copie(s)...")
        try:
            results = self.client.batch_grade(correct_answers, images_b64)
            self._append_output("Batch terminé.")
            
            # Clear treeview
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            self.batch_results = []
            
            for i, res in enumerate(results):
                student_id = res.get("student_id", "Unknown")
                awarded = res.get("score", 0)  # Make sure we use 'score', not 'total_awarded' as it is 'score' in schema
                answers = res.get("answers", {})
                answers_str = ", ".join([f"{k}: {v}" for k, v in answers.items()])
                raw_text = res.get("raw_text", "Aucun texte extrait disponible.")
                
                score_display = f"{awarded:.2f} / 20"

                # Display in Treeview
                # Let's save metadata for later save
                item = {
                    "student_id": student_id,
                    "student_name": f"Élève_{student_id}",
                    "score": awarded,
                    "score_display": score_display,
                    "feedback": "Batch graded",
                    "filename": filenames[i] if i < len(filenames) else "",
                    "raw_text": raw_text
                }
                self.batch_results.append(item)
                
                self.tree.insert("", tk.END, values=(
                    student_id,
                    item["student_name"],
                    item["score_display"],
                    answers_str,
                    self.current_class["name"] if self.current_class else "-",
                    self.current_subject["name"] if self.current_subject else "-"
                ))
        except Exception as exc:
            messagebox.showerror("Erreur Batch", str(exc))

    def _on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        if not values:
            return
            
        student_id = values[0]
        for r in self.batch_results:
            if str(r.get("student_id")) == str(student_id):
                self.extraction_text.delete("1.0", tk.END)
                text = r.get("raw_text", "")
                if text is None: text = "Aucun texte extrait."
                self.extraction_text.insert(tk.END, text)
                break
                
    def _on_double_click_tree(self, event):
        item_id = self.tree.focus()
        if not item_id: return
        values = list(self.tree.item(item_id, "values"))
        
        current_score_str = str(values[2]).replace(" / 20", "")
        new_score_str = simpledialog.askstring("Editer Note", f"Nouvelle note pour {values[1]} (sur 20):", initialvalue=current_score_str)
        if new_score_str is None: return
        try:
            new_score = float(new_score_str)
            if new_score < 0 or new_score > 20:
                messagebox.showwarning("Note Invalide", "La note doit être comprise entre 0 et 20.")
                return

            values[2] = f"{new_score:.2f} / 20"
            self.tree.item(item_id, values=values)
            
            # Update internal list
            student_id = values[0]
            for r in self.batch_results:
                if str(r.get("student_id")) == str(student_id):
                    r["score"] = new_score
                    r["score_display"] = values[2]
                    break
        except ValueError:
            messagebox.showwarning("Note Invalide", "Veuillez entrer un nombre valide.")

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
                student_id = vals[0]
                student_name = vals[1]
                score = float(str(vals[2]).replace(" / 20", ""))
                
                self.client.create_submission(
                    student_name=student_name,
                    score=score,
                    feedback="Batch",
                    subject_id=self.current_subject["id"]
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

    def _append_output(self, text: str) -> None:
        self.output.insert("end", "> " + text + "\n")
        self.output.see("end")
