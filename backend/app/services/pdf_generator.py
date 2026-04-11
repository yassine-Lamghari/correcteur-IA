import io
import zipfile
from typing import List

from fpdf import FPDF
import logging

class ExamPDFGenerator:
    """Service to generate the 3 PDFs: Exam Sheet, Blank Answer Sheet, and Correction Key."""

    @staticmethod
    def _create_base_pdf(title: str) -> FPDF:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", style="B", size=14)
        pdf.cell(0, 10, "Université Moulay Ismaïl - ENSAM Meknès", ln=True, align="C")
        pdf.set_font("helvetica", size=12)
        pdf.cell(0, 10, title, ln=True, align="C")
        pdf.ln(10)
        return pdf

    @staticmethod
    def generate_exam_sheet(exam: dict, include_answers: bool = False) -> bytes:
        """PDF 1 (Exam) or PDF 3 (Correction Key)"""
        title = "EXAMEN (Corrigé)" if include_answers else "Sujet d'Examen"
        pdf = ExamPDFGenerator._create_base_pdf(title)

        if not include_answers:
            pdf.set_font("helvetica", style="B", size=12)
            pdf.cell(0, 8, "Nom et Prénom : _____________________________", ln=True)
            pdf.ln(5)

        pdf.set_font("helvetica", size=11)
        for q in exam.get("questions", []):
            pdf.set_font("helvetica", style="B", size=11)
            pdf.multi_cell(0, 8, f"Q{q['id']}. {q['question']}")
            
            pdf.set_font("helvetica", size=11)
            options = {
                "A": q['option_A'],
                "B": q['option_B'],
                "C": q['option_C'],
                "D": q['option_D']
            }
            for letter, text in options.items():
                prefix = "[ X ] " if include_answers and q['correct_answer'].upper() == letter else "[   ] "
                if include_answers and q['correct_answer'].upper() == letter:
                    pdf.set_text_color(0, 128, 0) # Green for correct
                    pdf.set_font("helvetica", style="B", size=11)
                else:
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("helvetica", size=11)
                
                pdf.cell(20, 8, f"  {prefix}{letter}) ", align="R")
                pdf.multi_cell(0, 8, text)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        return pdf.output(dest="S")

    @staticmethod
    def generate_blank_answer_sheet(exam: dict) -> bytes:
        """PDF 2: The blank sheet for the students to fill, designed to be easily read by our OCR."""
        pdf = ExamPDFGenerator._create_base_pdf("Feuille de Réponses")

        # Header for the student
        pdf.set_font("helvetica", style="B", size=12)
        pdf.cell(0, 10, "Matricule (ID) : ____________________", ln=True)
        pdf.cell(0, 10, "Nom et Prénom : ____________________", ln=True)
        pdf.ln(10)

        # Instructions
        pdf.set_font("helvetica", size=10)
        pdf.cell(0, 6, "Inscrivez la lettre correspondant à votre réponse (A, B, C ou D) devant chaque question.", ln=True)
        pdf.ln(10)

        # Table for answers
        pdf.set_font("helvetica", size=12)
        
        pdf.cell(40, 10, f"QUESTIONS REPONSE", ln=True)
        
        pdf.ln(2)
        pdf.set_font("helvetica", style="B", size=14)
        for q in exam.get('questions', []):
            # We enforce the "1   " format for the answer placeholder.
            # The student will write A, B, C or D in the blank space
            pdf.cell(30, 10, f"{q['id']}", border=1, align="C")
            pdf.cell(30, 10, " ", border=1, align="C")
            pdf.ln(10)
        
        return pdf.output(dest="S")

    @staticmethod
    def create_exam_zip(exam: dict) -> io.BytesIO:
        """Compiles the 3 PDFs in a single ZIP in memory."""
        sujet_pdf = ExamPDFGenerator.generate_exam_sheet(exam, include_answers=False)
        corrige_pdf = ExamPDFGenerator.generate_exam_sheet(exam, include_answers=True)
        reponses_pdf = ExamPDFGenerator.generate_blank_answer_sheet(exam)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("Sujet_Examen.pdf", bytes(sujet_pdf))
            zip_file.writestr("Corrige_Professeur.pdf", bytes(corrige_pdf))
            zip_file.writestr("Feuille_Reponses_Vierge.pdf", bytes(reponses_pdf))
        
        zip_buffer.seek(0)
        return zip_buffer
