from __future__ import annotations

import base64
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

from autograde_tk.api_client import AutoGradeApiClient


class MainWindow(ttk.Frame):
    def __init__(self, master: tk.Tk, client: AutoGradeApiClient) -> None:
        super().__init__(master, padding=12)
        self.client = client
        self.selected_image_b64 = ""

        # Session State
        self.current_teacher = None
        self.current_class = None
        self.current_subject = None

        self.task = tk.StringVar(value="Text")
        self.student_name = tk.StringVar(value="Élève Anonyme")
        self.student_answer = tk.StringVar(value="")
        self.use_llm = tk.BooleanVar(value=True)

        self._build_ui()
        self._load_teachers()

    def _build_ui(self) -> None:
        self.grid(sticky="nsew")

        # --- Top Bar: Hierarchical Selectors ---
        top_frame = ttk.LabelFrame(self, text="Contexte Professeur", padding=8)
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        ttk.Label(top_frame, text="Professeur:").grid(row=0, column=0, padx=4, sticky="e")
        self.cb_teacher = ttk.Combobox(top_frame, state="readonly", width=15)
        self.cb_teacher.grid(row=0, column=1, padx=4)
        self.cb_teacher.bind("<<ComboboxSelected>>", self._on_teacher_selected)
        
        ttk.Button(top_frame, text="+", width=3, command=self._add_teacher).grid(row=0, column=2, padx=2)

        ttk.Label(top_frame, text="Classe:").grid(row=0, column=3, padx=4, sticky="e")
        self.cb_class = ttk.Combobox(top_frame, state="readonly", width=15)
        self.cb_class.grid(row=0, column=4, padx=4)
        self.cb_class.bind("<<ComboboxSelected>>", self._on_class_selected)
        
        ttk.Button(top_frame, text="+", width=3, command=self._add_class).grid(row=0, column=5, padx=2)

        ttk.Label(top_frame, text="Matière:").grid(row=0, column=6, padx=4, sticky="e")
        self.cb_subject = ttk.Combobox(top_frame, state="readonly", width=15)
        self.cb_subject.grid(row=0, column=7, padx=4)
        self.cb_subject.bind("<<ComboboxSelected>>", self._on_subject_selected)
        
        ttk.Button(top_frame, text="+", width=3, command=self._add_subject).grid(row=0, column=8, padx=2)

        # --- Middle Bar: Upload & OCR ---
        mid_frame = ttk.LabelFrame(self, text="Nouvelle Copie", padding=8)
        mid_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        ttk.Label(mid_frame, text="Nom d'étudiant:").grid(row=0, column=0, sticky="e", padx=4)
        ttk.Entry(mid_frame, textvariable=self.student_name, width=20).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Button(mid_frame, text="Importer Scanner", command=self._select_file).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        ttk.Button(mid_frame, text="Extraire Texte (GLM OCR)", command=self._run_ocr).grid(row=1, column=2, sticky="w", padx=4, pady=4)

        # --- Grading Section ---
        grade_frame = ttk.LabelFrame(self, text="Correction & Édition", padding=8)
        grade_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        
        ttk.Label(grade_frame, text="Consigne pour l'IA:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.question_prompt = tk.Text(grade_frame, height=2, width=60, wrap="word")
        self.question_prompt.insert(tk.END, "Veuillez corriger cette copie entière (QCM / Questions). Prenez en compte que l'élève a coché les cases avec '■'. Donnez la vraie note sur 20 !")
        self.question_prompt.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        ttk.Label(grade_frame, text="Réponse extraite:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.answer_text = tk.Text(grade_frame, height=4, width=60, wrap="word")
        self.answer_text.grid(row=3, column=0, columnspan=3, sticky="ew")

        opt_frame = ttk.Frame(grade_frame)
        opt_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        
        ttk.Radiobutton(opt_frame, text="Option 1 (Corrigé strict)", variable=self.use_llm, value=False).grid(row=0, column=0, padx=4)
        ttk.Radiobutton(opt_frame, text="Option 2 (Intelligence Gemini sans corrigé)", variable=self.use_llm, value=True).grid(row=0, column=1, padx=4)
        
        btn_action_frame = ttk.Frame(grade_frame)
        btn_action_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Button(btn_action_frame, text="Lancer la Correction", command=self._grade).grid(row=0, column=0, padx=4)
        ttk.Button(btn_action_frame, text="Générer Feedback LLM", command=self._feedback).grid(row=0, column=1, padx=4)
        ttk.Button(btn_action_frame, text="Enregistrer la Note !", command=self._save_submission).grid(row=0, column=2, padx=4)

        # --- Export Section ---
        export_frame = ttk.Frame(self)
        export_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        ttk.Button(export_frame, text="Exporter les notes en Excel", command=self._export_excel).grid(row=0, column=0, sticky="w")

        # --- Log Output ---
        self.output = tk.Text(self, height=12, wrap="word")
        self.output.grid(row=4, column=0, columnspan=3, sticky="nsew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

    # --- Hierarchy Methods ---
    def _load_teachers(self):
        try:
            self.teachers = self.client.get_teachers()
            self.cb_teacher["values"] = [t["name"] for t in self.teachers]
        except Exception as e:
            self._append_output(f"Error loading teachers: {e}")

    def _on_teacher_selected(self, event):
        idx = self.cb_teacher.current()
        if idx >= 0:
            self.current_teacher = self.teachers[idx]
            self._load_classes()

    def _load_classes(self):
        if not self.current_teacher: return
        try:
            self.classes = self.client.get_classes(self.current_teacher["id"])
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

    def _add_teacher(self):
        name = simpledialog.askstring("Nouveau Professeur", "Nom du professeur:")
        email = simpledialog.askstring("Nouveau Professeur", "Email:")
        if name and email:
            self.client.create_teacher(name, email)
            self._load_teachers()

    def _add_class(self):
        if not self.current_teacher:
            messagebox.showwarning("Attention", "Sélectionnez un professeur d'abord.")
            return
        name = simpledialog.askstring("Nouvelle Classe", "Nom de la classe (ex: Math 101):")
        if name:
            self.client.create_class(name, self.current_teacher["id"])
            self._load_classes()

    def _add_subject(self):
        if not self.current_class:
            messagebox.showwarning("Attention", "Sélectionnez une classe d'abord.")
            return
        name = simpledialog.askstring("Nouvelle Matière", "Nom du modèle/matière:")
        if name:
            self.client.create_subject(name, self.current_class["id"])
            self._load_subjects()

    # --- OCR, Grading & Actions ---
    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Sélectionner une copie scannée",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")],
        )
        if not path:
            return

        with open(path, "rb") as file:
            self.selected_image_b64 = base64.b64encode(file.read()).decode("utf-8")
        self._append_output(f"Fichier chargé: {path}")

    def _run_ocr(self) -> None:
        if not self.selected_image_b64:
            messagebox.showwarning("Fichier manquant", "Veuillez importer une image.")
            return
        try:
            self._append_output("Extraction OCR GLM en cours...")
            result = self.client.ocr(self.selected_image_b64, "Text")
            raw = result.get('raw_text', '')
            self._append_output(f"Texte OCR brut :\n{raw}")
            answers = result.get("extracted_answers", [])
            
            # fallback string
            text_val = answers[0] if answers else raw
            self.answer_text.delete("1.0", tk.END)
            self.answer_text.insert(tk.END, text_val)
        except Exception as exc:
            messagebox.showerror("Erreur OCR GLM", str(exc))

    def _grade(self) -> None:
        student_ans = self.answer_text.get("1.0", tk.END).strip()
        current_prompt = self.question_prompt.get("1.0", tk.END).strip()
        
        if not student_ans:
            messagebox.showwarning("Erreur", "Aucune réponse à corriger.")
            return
            
        question = {
            "question_id": "q1",
            "type": "essay",
            "prompt": current_prompt,
            "max_points": 20,
            "expected_answer": "",
            "keywords": [],
        }
        
        # If Option 1 without key:
        if not self.use_llm.get():
            question["keywords"] = ["MVC", "Backend", "Frontend", "Base de données", "API"]

        try:
            self._append_output("Correction en cours avec " + ("Gemini" if self.use_llm.get() else "Barème Mots-Clés") + "...")
            grade = self.client.grade(question, student_ans, use_llm=self.use_llm.get())
            self._append_output(f"Résultat: {grade['awarded_points']} / 20. Confiance: {grade['confidence']}")
            
            self.last_grade = grade
            # Generate inline feedback immediately
            if self.use_llm.get() and 'feedback' in grade:
                 self.last_feedback = grade.get("feedback")
        except Exception as exc:
            messagebox.showerror("Erreur de Correction", str(exc))

    def _feedback(self) -> None:
        grade = getattr(self, "last_grade", None)
        if not grade:
            messagebox.showwarning("Erreur", "Veuillez corriger la copie en premier.")
            return
            
        student_ans = self.answer_text.get("1.0", tk.END).strip()
        current_prompt = self.question_prompt.get("1.0", tk.END).strip()
        
        question = {
            "question_id": "q1",
            "type": "essay",
            "prompt": current_prompt,
            "max_points": 20,
        }

        try:
            self._append_output("Génération du feedback...")
            result = self.client.feedback(question, student_ans, grade)
            self.last_feedback = result.get("feedback", "")
            self._append_output(f"Feedback LLM : {self.last_feedback}")
        except Exception as exc:
            messagebox.showerror("Erreur Feedback", str(exc))

    def _save_submission(self) -> None:
        if not self.current_subject:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une matière.")
            return
            
        if not hasattr(self, "last_grade"):
            messagebox.showwarning("Erreur", "Aucune correction n'est prête à être enregistrée.")
            return
            
        try:
            fb = getattr(self, "last_feedback", getattr(self, "last_grade", {}).get("feedback", ""))
            score = float(self.last_grade.get("awarded_points", 0))
            self.client.create_submission(
                student_name=self.student_name.get(),
                score=score,
                feedback=fb,
                subject_id=self.current_subject["id"]
            )
            self._append_output(f"✅ Note de {self.student_name.get()} enregistrée avec succès ({score} pts) dans la matière {self.current_subject['name']}.")
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
