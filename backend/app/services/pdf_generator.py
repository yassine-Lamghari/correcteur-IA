import io
import zipfile
from typing import List

from fpdf import FPDF
import logging

def sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    replacements = {
        '‘': "'", '’': "'", '‚': "'", '‛': "'",
        '“': '"', '”': '"', '„': '"', '‟': '"', '«': '"', '»': '"',
        '–': '-', '—': '-', '−': '-',
        '…': '...',
        '€': 'EUR',
        '•': '-', '◦': '-',
        '✓': 'v', '✔': 'v',
        '\u2028': '', '\u2029': ''
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('windows-1252', 'ignore').decode('windows-1252')

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
            pdf.set_x(10)
            clean_question = sanitize_text(str(q.get('question', '')))
            clean_id = sanitize_text(str(q.get('id', '')))
            pdf.multi_cell(0, 8, f"Q{clean_id}. {clean_question}")
            
            pdf.set_font("helvetica", size=11)
            options = {
                "A": sanitize_text(str(q.get('option_A', ''))),
                "B": sanitize_text(str(q.get('option_B', ''))),
                "C": sanitize_text(str(q.get('option_C', ''))),
                "D": sanitize_text(str(q.get('option_D', '')))
            }
            for letter, text in options.items():
                prefix = "[ X ] " if include_answers and q['correct_answer'].upper() == letter else "[   ] "
                if include_answers and q['correct_answer'].upper() == letter:
                    pdf.set_text_color(0, 128, 0) # Green for correct
                    pdf.set_font("helvetica", style="B", size=11)
                else:
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("helvetica", size=11)
                
                # Combine prefix and text into a single multi_cell call to avoid fpdf horizontal space error
                formatted_text = f"      {prefix}{letter}) {text}"
                pdf.set_x(10)
                pdf.multi_cell(0, 8, formatted_text)
            
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


class CoursePDFGenerator:
    """PDF d'un cours généré (contenu Markdown simplifié pour l'impression)."""

    @staticmethod
    def _strip_inline_md(text: str) -> str:
        t = text.replace("**", "").replace("__", "")
        if t.startswith("- "):
            t = "• " + t[2:]
        return t

    @staticmethod
    def render_markdown_to_pdf(title: str, markdown_body: str) -> bytes:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("helvetica", style="B", size=14)
        pdf.cell(0, 10, sanitize_text("Université Moulay Ismaïl - ENSAM Meknès"), ln=True, align="C")
        pdf.set_font("helvetica", style="B", size=16)
        pdf.multi_cell(0, 10, sanitize_text(title or "Cours"))
        pdf.ln(4)

        lines = (markdown_body or "").splitlines()
        in_code = False
        code_buf: List[str] = []

        def flush_code() -> None:
            nonlocal code_buf
            if not code_buf:
                return
            pdf.set_font("courier", size=9)
            block = "\n".join(code_buf)
            pdf.multi_cell(0, 5, sanitize_text(block))
            pdf.ln(2)
            code_buf = []
            pdf.set_font("helvetica", size=11)

        i = 0
        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()

            if stripped.startswith("```"):
                if in_code:
                    flush_code()
                    in_code = False
                else:
                    in_code = True
                i += 1
                continue

            if in_code:
                code_buf.append(raw)
                i += 1
                continue

            if not stripped:
                pdf.ln(2)
                i += 1
                continue

            if stripped.startswith("# "):
                pdf.set_font("helvetica", style="B", size=15)
                pdf.multi_cell(0, 8, sanitize_text(CoursePDFGenerator._strip_inline_md(stripped[2:].strip())))
                pdf.ln(2)
            elif stripped.startswith("## "):
                pdf.set_font("helvetica", style="B", size=13)
                pdf.multi_cell(0, 7, sanitize_text(CoursePDFGenerator._strip_inline_md(stripped[3:].strip())))
                pdf.ln(1)
            elif stripped.startswith("### "):
                pdf.set_font("helvetica", style="B", size=11)
                pdf.multi_cell(0, 6, sanitize_text(CoursePDFGenerator._strip_inline_md(stripped[4:].strip())))
                pdf.ln(1)
            elif stripped.startswith(("- ", "* ", "• ")):
                pdf.set_font("helvetica", size=11)
                pdf.multi_cell(0, 6, sanitize_text(CoursePDFGenerator._strip_inline_md(stripped)))
                pdf.ln(0.5)
            else:
                pdf.set_font("helvetica", size=11)
                pdf.multi_cell(0, 6, sanitize_text(CoursePDFGenerator._strip_inline_md(stripped)))
                pdf.ln(0.5)

            i += 1

        if in_code and code_buf:
            flush_code()

        return pdf.output(dest="S")
