import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox, filedialog
import threading

class ExamTab(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=10)
        self.api_client = api_client
        self.current_exam = None
        self._build_ui()

    def _build_ui(self):
        # Top Frame: Input Context
        top_frame = ttk.Labelframe(self, text="Paramètres de l'Examen", padding=15, bootstyle="info")
        top_frame.pack(side=tk.TOP, fill="x", pady=(0, 15))

        ttk.Label(top_frame, text="Nombre de questions :", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.num_q_var = tk.IntVar(value=10)
        ttk.Spinbox(top_frame, from_=1, to_=50, textvariable=self.num_q_var, width=8, bootstyle="primary").grid(row=0, column=1, sticky="w", pady=5, padx=10)

        self.course_content = ""

        ttk.Label(top_frame, text="Support de cours (PDF) :", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="nw", pady=10)
        
        pdf_frame = ttk.Frame(top_frame)
        pdf_frame.grid(row=1, column=1, sticky="ew", pady=10, padx=10)
        
        self.pdf_label = ttk.Label(pdf_frame, text="Aucun fichier sélectionné", font=("Segoe UI", 10, "italic"))
        self.pdf_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(pdf_frame, text="Parcourir...", command=self._import_pdf, bootstyle="outline-primary").pack(side=tk.LEFT)

        ttk.Label(top_frame, text="Consigne à Gemini :", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="nw", pady=5)
        self.instructions_text = tk.Text(top_frame, height=5, width=80, font=("Segoe UI", 10))
        self.instructions_text.grid(row=2, column=1, pady=5, padx=10, sticky="ew")
        
        btn_generate = ttk.Button(top_frame, text="✨ Générer le QCM via Gemini", command=self._generate_exam, bootstyle="success", cursor="hand2")
        btn_generate.grid(row=3, column=1, sticky="e", pady=5, padx=10)

        # Bottom Frame: Export options (Pack it BEFORE the middle frame so it's always visible!)
        bot_frame = ttk.Frame(self, padding=10)
        bot_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.btn_export = ttk.Button(bot_frame, text="📥 Sauvegarder les PDFs et Base de Données", state=tk.DISABLED, command=self._export_pdfs, bootstyle="primary", cursor="hand2")
        self.btn_export.pack(side=tk.RIGHT)

        # Middle Frame: Treeview to display and edit questions
        mid_frame = ttk.Labelframe(self, text="Questions Générées (Double-cliquez pour modifier)", padding=15, bootstyle="secondary")
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)

        columns = ("ID", "Question", "A", "B", "C", "D", "Réponse")
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="headings", height=10, bootstyle="info")
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "ID":
                self.tree.column(col, width=40, anchor="center")
            elif col == "Réponse":
                self.tree.column(col, width=80, anchor="center")
            else:
                self.tree.column(col, width=150)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_double_click)

    def _import_pdf(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Fichiers PDF", "*.pdf")],
            title="Sélectionner le cours au format PDF"
        )
        if not filepath:
            return
            
        try:
            text = self.api_client.extract_text_from_pdf(filepath)
            if not text.strip():
                messagebox.showwarning("Attention", "Aucun texte n'a pu être extrait de ce PDF.")
                return
                
            self.course_content = text
            # Extract just filename for the label
            filename = filepath.replace('\\', '/').split('/')[-1]
            self.pdf_label.config(text=filename)
            messagebox.showinfo("Succès", "Texte extrait du PDF et ajouté au contexte en arrière-plan.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la lecture du PDF :\n{e}")

    def _generate_exam(self):
        instructions = self.instructions_text.get("1.0", tk.END).strip()
        if not self.course_content:
            messagebox.showwarning("Attention", "Veuillez d'abord importer un support de cours (PDF).")
            return

        num_questions = self.num_q_var.get()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.btn_export.config(state=tk.DISABLED)

        def task():
            try:
                self.current_exam = self.api_client.generate_exam(self.course_content, instructions, num_questions)
                self._populate_tree()
                self.btn_export.config(state=tk.NORMAL)
                messagebox.showinfo("Succès", "Examen généré avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la génération : {e}")

        threading.Thread(target=task, daemon=True).start()

    def _populate_tree(self):
        if not self.current_exam or "questions" not in self.current_exam:
            return
        
        for q in self.current_exam["questions"]:
            self.tree.insert("", "end", iid=str(q["id"]), values=(
                q["id"],
                q["question"],
                q["option_A"],
                q["option_B"],
                q["option_C"],
                q["option_D"],
                q["correct_answer"]
            ))

    def _on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        column = self.tree.identify_column(event.x)
        col_idx = int(column.replace('#', '')) - 1
        
        # Don't edit ID
        if col_idx == 0:
            return
            
        col_name = self.tree['columns'][col_idx]
        current_value = self.tree.item(item, 'values')[col_idx]

        # Simple popup to edit
        edit_win = tk.Toplevel(self)
        edit_win.title(f"Modifier {col_name}")
        edit_win.geometry("400x150")
        
        entry = ttk.Entry(edit_win, width=50)
        entry.insert(0, current_value)
        entry.pack(padx=20, pady=20)
        
        def save():
            new_val = entry.get()
            vals = list(self.tree.item(item, 'values'))
            vals[col_idx] = new_val
            self.tree.item(item, values=vals)
            
            # Update the underlying dict
            q_id = int(vals[0])
            for q in self.current_exam["questions"]:
                if q["id"] == q_id:
                    key_map = {1: "question", 2: "option_A", 3: "option_B", 4: "option_C", 5: "option_D", 6: "correct_answer"}
                    q[key_map[col_idx]] = new_val
                    break
            
            edit_win.destroy()
            
        ttk.Button(edit_win, text="Sauvegarder", command=save).pack()

    def _export_pdfs(self):
        if not self.current_exam:
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Fichier ZIP", "*.zip")],
            initialfile="Exam_QCM_complet.zip",
            title="Enregistrer l'archive PDF"
        )
        if not filepath:
            return
            
        def task():
            try:
                zip_bytes = self.api_client.export_exam_pdfs(self.current_exam)
                with open(filepath, "wb") as f:
                    f.write(zip_bytes)
                messagebox.showinfo("Export Réussi", f"Fichiers enregistrés dans : {filepath}")
            except Exception as e:
                messagebox.showerror("Erreur d'export", f"Impossible d'exporter les PDF : {e}")
                
        threading.Thread(target=task, daemon=True).start()