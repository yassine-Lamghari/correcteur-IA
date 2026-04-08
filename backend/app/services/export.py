import pandas as pd
from typing import List
from io import BytesIO

from app.models.domain import Submission
from app.models.schemas import Subject

class ExportService:
    @staticmethod
    def generate_excel(submissions: List[Submission], subject: Subject, class_name: str) -> BytesIO:
        data = []
        for sub in submissions:
            data.append({
                "Étudiant": sub.student_name,
                "Note": sub.score if sub.score is not None else "Non noté",
                "Matière": subject.name,
                "Classe": class_name,
                "Feedback": sub.feedback or ""
            })
            
        df = pd.DataFrame(data)
        
        output = BytesIO()
        # pandas correctly uses openpyxl engine
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Notes')
            
        output.seek(0)
        return output