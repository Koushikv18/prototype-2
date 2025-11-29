# quick test script (save as test_pdf.py in project folder)
from langchain_pipeline import save_report_pdf
out = {
    "structured": {"symptoms": "chest pain", "duration": "2 days", "severity":"mild"},
    "triage": {"specialist":"General", "urgency":"low"},
    "conversation": [("bot","What is the symptom?"), ("patient","Chest pain since yesterday")] 
}
print(save_report_pdf(out, path="outputs/test_report.pdf"))
