import pandas as pd
import statistics
from typing import List
from io import BytesIO

from app.models.domain import Submission
from app.models.schemas import Subject

class ExportService:
    @staticmethod
    def generate_excel(submissions: List[Submission], subject: Subject, class_name: str) -> BytesIO:
        data = []
        scores = []
        for sub in submissions:
            data.append({
                "Étudiant": sub.student_name,
                "Note": sub.score if sub.score is not None else "Non noté",
                "Matière": subject.name,
                "Classe": class_name,
                "Feedback": sub.feedback or ""
            })
            if sub.score is not None:
                scores.append(sub.score)
            
        df = pd.DataFrame(data)
        
        output = BytesIO()
        # pandas correctly uses openpyxl engine
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Notes')

            summary = ExportService._build_summary(scores)
            pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name='Resume')

            dist = ExportService._build_distribution(scores)
            pd.DataFrame(dist).to_excel(writer, index=False, sheet_name='Distribution')
            
        output.seek(0)
        return output

    @staticmethod
    def _build_summary(scores: List[float]) -> dict:
        if not scores:
            return {
                "Effectif": 0,
                "Moyenne": 0.0,
                "Mediane": 0.0,
                "Min": 0.0,
                "Max": 0.0,
                "Ecart-type": 0.0,
                "Taux de reussite": 0.0,
            }

        count = len(scores)
        mean = sum(scores) / count
        median = statistics.median(scores)
        min_val = min(scores)
        max_val = max(scores)
        stdev = statistics.pstdev(scores) if count > 1 else 0.0
        pass_rate = sum(1 for s in scores if s >= 10.0) / count * 100.0
        return {
            "Effectif": count,
            "Moyenne": round(mean, 2),
            "Mediane": round(median, 2),
            "Min": round(min_val, 2),
            "Max": round(max_val, 2),
            "Ecart-type": round(stdev, 2),
            "Taux de reussite": round(pass_rate, 1),
        }

    @staticmethod
    def _build_distribution(scores: List[float]) -> List[dict]:
        bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20.1)]
        count = len(scores)
        rows = []
        for start, end in bins:
            label = f"{int(start)}-{int(end) if end < 20.1 else 20}"
            bin_scores = [s for s in scores if start <= s < end]
            percent = (len(bin_scores) / count * 100.0) if count else 0.0
            rows.append({
                "Tranche": label,
                "Effectif": len(bin_scores),
                "Pourcentage": round(percent, 1),
            })
        return rows