# langchain_pipeline.py
# FINAL CLEAN VERSION — ML QUESTIONS + SAFE PDF + NO TTF REQUIRED

import os, json, re, datetime
from dotenv import load_dotenv
import requests

load_dotenv()

# --------------------- Ollama Config ---------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

def call_ollama(prompt, max_tokens=120, temperature=0.3, timeout=60):
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        data = r.json()
        return data.get("response", "").strip()
    except Exception:
        return "I'm sorry, I couldn't process that."


# -----------------------------------------------------------
#              ML-DRIVEN QUESTION GENERATOR (SAFE)
# -----------------------------------------------------------

def generate_conversational_reply(
    chat_messages,
    user_message,
    k_context: int = 3,
    max_turns: int = 6,
    temperature: float = 0.3,
):
    """
    ML-driven dynamic question generator using Ollama.
    Stops after 5 patient replies.
    """

    # Count patient replies
    patient_answers = sum(1 for r, _ in chat_messages if r == "patient")

    if patient_answers >= 5:
        return "Thank you. I have collected all required information."

    # Build conversation history safely
    convo = ""
    for role, text in chat_messages:
        tag = "Patient" if role == "patient" else "Bot"
        convo += f"{tag}: {text}\n"

    # Build safe prompt
    prompt = (
        "You are NIVA, an intelligent medical intake assistant.\n"
        "Your job is to ask ONLY 1 medically relevant follow-up question.\n"
        "Use the last answer.\n"
        "Do NOT give diagnosis.\n"
        "Do NOT explain.\n"
        "Ask exactly ONE clear medical question.\n\n"
        "Conversation so far:\n"
        + convo +
        "\nPatient just said: \"" + user_message + "\"\n"
        "Now ask the next medically relevant question."
    )

    reply = call_ollama(prompt, max_tokens=80, temperature=temperature)

    # Remove accidental prefixes
    if ":" in reply:
        reply = reply.split(":", 1)[-1].strip()

    return reply


# -----------------------------------------------------------
#                     STRUCTURED EXTRACTION
# -----------------------------------------------------------

def extract_structured_from_conversation(conv_text: str):
    lines = conv_text.split("\n")
    answers = [
        line.split(":", 1)[1].strip()
        for line in lines if line.startswith("Patient:")
    ]

    while len(answers) < 5:
        answers.append("")

    structured = {
        "symptoms": answers[0],
        "duration": answers[1],
        "severity": answers[2],
        "additional_symptoms": answers[3],
        "medical_history": answers[4],
    }

    sev = structured["severity"].lower()
    if "severe" in sev:
        structured["urgency"] = "high"
    elif "moderate" in sev:
        structured["urgency"] = "medium"
    else:
        structured["urgency"] = "low"

    return structured


# -----------------------------------------------------------
#                        TRIAGE
# -----------------------------------------------------------

def triage_report(structured: dict):
    urg = structured.get("urgency", "low")

    if urg == "high":
        return {"specialist": "Emergency Care", "urgency": "high"}
    if urg == "medium":
        return {"specialist": "General Physician", "urgency": "medium"}
    return {"specialist": "General Physician", "urgency": "low"}


# -----------------------------------------------------------
#                      SAVE JSON
# -----------------------------------------------------------

def save_report(out: dict, path="outputs/report.json"):
    os.makedirs("outputs", exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    return path


# -----------------------------------------------------------
#                     SAFE PDF GENERATOR
# -----------------------------------------------------------

def save_report_pdf(out: dict, path: str = None):
    from fpdf import FPDF
    import os, json, datetime, re

    def clean(t):
        if not isinstance(t, str):
            t = str(t)
        # Replace unsupported Unicode
        t = t.replace("—", "-").replace("–", "-")
        t = t.replace("“", '"').replace("”", '"')
        t = t.replace("‘", "'").replace("’", "'")
        # Remove control chars
        t = re.sub(r"[\x00-\x1F\x7F]", " ", t)
        # Ensure Latin-1 safe
        t = t.encode("latin-1", "ignore").decode("latin-1")
        return t.strip()

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    if path is None:
        path = f"outputs/niva_report_{ts}.pdf"

    os.makedirs("outputs", exist_ok=True)

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(0, 90, 160)
            self.rect(0, 0, 210, 25, "F")
            self.set_text_color(255, 255, 255)
            self.set_font("Arial", "B", 18)
            self.cell(0, 12, "NIVA Medical Consultation Report", align="C", ln=True)
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, "Generated by NIVA Healthcare System © 2025", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    structured = out["structured"]
    triage = out["triage"]
    conv = out["conversation"]

    def section_title(text):
        pdf.set_fill_color(230, 245, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, text, ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Arial", "", 12)

    LEFT = 10
    WIDTH = 150

    # ---------------- STRUCTURED INFORMATION ----------------
    section_title("Structured Information")

    info_items = [
        ("Symptoms", structured.get("symptoms", "")),
        ("Duration", structured.get("duration", "")),
        ("Severity", structured.get("severity", "")),
        ("Additional Symptoms", structured.get("additional_symptoms", "")),
        ("Medical History", structured.get("medical_history", "")),
    ]

    for label, value in info_items:
        pdf.set_x(LEFT)
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(WIDTH, 7, f"{label}:")

        pdf.set_x(LEFT)
        pdf.set_font("Arial", "", 12)
        safe_value = clean(value) if value.strip() else "-"
        pdf.multi_cell(WIDTH, 7, safe_value)

        pdf.ln(2)

    # ---------------- TRIAGE RECOMMENDATION ----------------
    section_title("Triage Recommendation")

    for key, val in triage.items():
        pdf.set_x(LEFT)
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(WIDTH, 7, f"{key.title()}:")

        pdf.set_x(LEFT)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(WIDTH, 7, clean(str(val)))

        pdf.ln(2)

    # ---------------- CONVERSATION TRANSCRIPT ----------------
    section_title("Conversation Transcript")

    for role, text in conv:
        who = "Patient" if role == "patient" else "NIVA"
        pdf.multi_cell(180, 7, f"{who}: {clean(text)}")
        pdf.ln(1)

    pdf.ln(10)
    pdf.set_font("Arial", "I", 11)
    pdf.cell(0, 8, f"Report ID: RPT-{ts}", ln=True)

    pdf.output(path)
    return path
