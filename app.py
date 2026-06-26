import os
import json
import random
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime

from io import BytesIO

from flask import send_file

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from flask import (
    Flask,
    render_template,
    request,
    session,
    jsonify,
    redirect,
    url_for
)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "SECRET_KEY",
    "exam_engine_secret"
)

GROQ_KEYS = [
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3")

]

GROQ_KEYS = [k for k in GROQ_KEYS if k]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

def clear_exam():
    session.pop("quiz", None)
    session.pop("answers", None)
    session.pop("result", None)
    session.pop("start_time", None)
    session.pop("exam_meta", None)

def initialize_exam():
    session["quiz"] = []
    session["answers"] = {}
    session["result"] = {}
    session["start_time"] = datetime.now().isoformat()

def call_groq(messages, temperature=0.7):
    last_error = None
    for key in GROQ_KEYS:
        try:
            response = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"

                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": temperature
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("Rate Limited... Switching Key")
                continue
            else:
                last_error = response.text
        except Exception as e:
            last_error = str(e)

    raise Exception(last_error)


def extract_json(text):
    text = text.strip()
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        raise Exception("JSON Not Found")
    return json.loads(
        text[start:end+1]
    )

def build_prompt(
    topic,
    subtopic,
    difficulty,
    number_of_questions
):
    return f"""
You are an expert exam paper setter.

Generate EXACTLY {number_of_questions} high-quality Multiple Choice Questions.

Topic:
{topic}

Subtopic:
{subtopic if subtopic else "General"}

Difficulty:
{difficulty}

Instructions:

1. Generate EXACTLY {number_of_questions} questions.
2. Every question must have exactly 4 options.
3. Only ONE option must be correct.
4. Correct answer must be one of:
   "A", "B", "C", or "D".
5. Shuffle the correct option randomly across A, B, C and D.
6. Questions must NOT be repeated.
7. Questions should test conceptual understanding rather than memorization.
8. Avoid ambiguous questions.
9. Avoid options like "All of the above", "None of the above", "Both A and B", etc.
10. Every option should be meaningful and plausible.
11. Do NOT use markdown.
12. Do NOT wrap the JSON inside ```json blocks.
13. Return ONLY valid JSON.
14. Do not write any extra text before or after the JSON.

For every question provide:

- question
- options
- correct answer
- explanation for EACH option
- overall concept explanation

JSON FORMAT:

[
    {{
        "question": "Question text",

        "options": [
            "Option A",
            "Option B",
            "Option C",
            "Option D"
        ],

        "correct": "A",

        "option_explanations": {{
            "A": "Explain why Option A is correct or incorrect.",
            "B": "Explain why Option B is correct or incorrect.",
            "C": "Explain why Option C is correct or incorrect.",
            "D": "Explain why Option D is correct or incorrect."
        }},

        "discussion": "Explain the complete concept behind this question in 80-150 words. Teach the concept instead of merely restating the answer."
    }}
]

Rules for option_explanations:

• If an option is correct, explain WHY it is correct.
• If an option is incorrect, explain WHY it is incorrect.
• Never simply say "Incorrect."
• Mention the concept or reasoning.
• Each explanation should be 15-40 words.

Rules for discussion:

• Explain the underlying concept clearly.
• Mention why the correct answer works.
• Mention common misconceptions if relevant.
• Keep it educational.
• Length: 80-150 words.

Return ONLY the JSON array.
"""
def validate_questions(questions):
    valid = []

    for q in questions:

        required = [
            "question",
            "options",
            "correct",
            "discussion",
            "option_explanations"
        ]

        if not all(key in q for key in required):
            continue

        if len(q["options"]) != 4:
            continue

        if q["correct"] not in ["A", "B", "C", "D"]:
            continue

        if not isinstance(q["option_explanations"], dict):
            continue

        if not all(k in q["option_explanations"] for k in ["A", "B", "C", "D"]):
            continue

        valid.append(q)

    return valid

def calculate_time_taken():

    if "start_time" not in session:
        return "0 min"

    start = datetime.fromisoformat(
        session["start_time"]
    )
    end = datetime.now()
    seconds = int((end-start).total_seconds())
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}m {sec}s"

def calculate_result():
    quiz = session.get("quiz", [])
    answers = session.get("answers", {})
    correct = 0
    wrong = 0
    skipped = 0
    review = []

    for index, question in enumerate(quiz):
        selected = answers.get(str(index), "")
        actual = question["correct"]
        status = selected == actual

        if selected == "":
            pass
        elif status:
            correct += 1
        else:
            wrong += 1

        letters = ["A", "B", "C", "D"]

        review.append({
            "question_number": index + 1,
            "question": question["question"],
            "options": question["options"],
            "selected": selected,
            "selected_index": letters.index(selected) if selected in letters else -1,
            "correct": actual,
            "correct_index": letters.index(actual),
            "discussion": question["discussion"],
            "option_explanations": question.get("option_explanations", {}),
            "status": status,
            "attempted": selected != ""
        })
    total = len(quiz)
    accuracy = 0
    if total:
        accuracy = round((correct/total)*100,2)
    result = {
        "score": correct,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "attempted": correct + wrong,
        "total": total,
        "accuracy": accuracy,
        "time": calculate_time_taken(),
        "review": review
    }
    circumference = 264

    result["circle_offset"] = round(circumference -(accuracy / 100) * circumference,2)
    session["result"] = result
    return result

def json_success(data=None):
    return jsonify({
        "success":True,
        "data":data
    })


def json_error(message):
    return jsonify({
        "success":False,
        "message":message
    })



@app.route("/")
def home():
    clear_exam()
    return render_template("landing.html")

@app.route("/generate", methods=["POST"])
def generate():

    try:
        data = request.get_json()
        topic = data.get("topic")
        subtopic = data.get("subtopic", "")
        difficulty = data.get("difficulty")
        number = int(data.get("questions"))
        initialize_exam()
        prompt = build_prompt(
            topic,
            subtopic,
            difficulty,
            number
        )
        messages = [
            {
                "role":"system",
                "content":"You generate high quality MCQs."
            },
            {
                "role":"user",
                "content":prompt
            }
        ]
        response = call_groq(messages)
        content = response["choices"][0]["message"]["content"]
        questions = extract_json(content)
        questions = validate_questions(
            questions
        )
        session["quiz"] = questions
        selected_time = data.get("duration","auto")

        difficulty_time={
            "Easy":90,
            "Medium":60,
            "Hard":30
        }

        if selected_time=="auto":
            duration = number * difficulty_time.get(difficulty,60)

        else:
            duration = int(selected_time)*60

        session["exam_meta"]={
            "topic":topic,
            "difficulty":difficulty,
            "total":number,
            "duration":duration
        }
        return json_success({
            "redirect":"/exam"
        })

    except Exception as e:
        return json_error(str(e))

@app.route("/exam")
def exam():
    if "quiz" not in session:
        return redirect("/")
    return render_template("main.html")

@app.route("/questions")
def questions():
    if "quiz" not in session:
        return json_error(
            "No Quiz Found"
        )
    quiz = session["quiz"]
    data = []
    for q in quiz:
        data.append({
            "question":q["question"],
            "options":q["options"]
        })
    meta = session.get("exam_meta", {})

    return json_success({
        "questions": data,
        "topic": meta.get("topic", ""),
        "difficulty": meta.get("difficulty", "Medium"),
        "total": meta.get("total", len(data)),
        "duration": meta.get("duration", len(data) * 60)
    })

@app.route("/download/questions")
def download_questions():

    quiz = session.get("quiz", [])
    meta = session.get("exam_meta", {})

    now = datetime.now()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph("<b><font size=20>QuizAI Question Paper</font></b>", styles["Title"])
    )

    story.append(Spacer(1, 18))

    story.append(Paragraph(f"<b>Topic:</b> {meta.get('topic','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Difficulty:</b> {meta.get('difficulty','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total Questions:</b> {len(quiz)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Exam Duration:</b> {meta.get('duration',0)//60} Minutes", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {now.strftime('%d %B %Y')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Time:</b> {now.strftime('%I:%M %p')}", styles["Normal"]))

    story.append(Spacer(1, 20))

    letters = ["A","B","C","D"]

    for i,q in enumerate(quiz):

        story.append(
            Paragraph(
                f"<b>Question {i+1}</b>",
                styles["Heading2"]
            )
        )

        story.append(
            Paragraph(
                q["question"],
                styles["BodyText"]
            )
        )

        story.append(Spacer(1,6))

        for j,opt in enumerate(q["options"]):

            story.append(
                Paragraph(
                    f"{letters[j]}. {opt}",
                    styles["BodyText"]
                )
            )

        story.append(Spacer(1,16))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Question_Paper_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf",
        mimetype="application/pdf"
    )

@app.route("/download/answers")
def download_answers():

    quiz = session.get("quiz", [])
    meta = session.get("exam_meta", {})

    now = datetime.now()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b><font size=20>QuizAI Solution Booklet</font></b>",
            styles["Title"]
        )
    )

    story.append(Spacer(1,18))

    story.append(Paragraph(f"<b>Topic:</b> {meta.get('topic','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Difficulty:</b> {meta.get('difficulty','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total Questions:</b> {len(quiz)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Exam Duration:</b> {meta.get('duration',0)//60} Minutes", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {now.strftime('%d %B %Y')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Time:</b> {now.strftime('%I:%M %p')}", styles["Normal"]))

    story.append(Spacer(1,20))

    letters=["A","B","C","D"]

    for i,q in enumerate(quiz):

        story.append(
            Paragraph(
                f"<b>Question {i+1}</b>",
                styles["Heading2"]
            )
        )

        story.append(
            Paragraph(
                q["question"],
                styles["BodyText"]
            )
        )

        story.append(Spacer(1,6))

        for j,opt in enumerate(q["options"]):

            story.append(
                Paragraph(
                    f"{letters[j]}. {opt}",
                    styles["BodyText"]
                )
            )

        story.append(Spacer(1,8))

        story.append(
            Paragraph(
                f"<b>Correct Answer:</b> {q['correct']}",
                styles["BodyText"]
            )
        )

        story.append(Spacer(1,6))

        story.append(
            Paragraph(
                "<b>Option-wise Explanation</b>",
                styles["Heading3"]
            )
        )

        option_exp = q.get("option_explanations", {})

        for letter in letters:

            explanation = option_exp.get(letter, "Not Available")

            story.append(
                Paragraph(
                    f"<b>{letter}.</b> {explanation}",
                    styles["BodyText"]
                )
            )

        story.append(Spacer(1,8))

        story.append(
            Paragraph(
                "<b>Concept Discussion</b>",
                styles["Heading3"]
            )
        )

        story.append(
            Paragraph(
                q["discussion"],
                styles["BodyText"]
            )
        )

        story.append(Spacer(1,18))

        story.append(
            Paragraph(
                "<font color='grey'>--------------------------------------------------------------</font>",
                styles["BodyText"]
            )
        )

        story.append(Spacer(1,12))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Solution_Booklet_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf",
        mimetype="application/pdf"
    )

@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json()
        session["answers"] = data.get(
            "answers",
            {}
        )
        calculate_result()

        return json_success({
            "redirect":"/results"
        })
    except Exception as e:
        return json_error(
            str(e)
        )

@app.route("/results")
def results():
    if "result" not in session:
        return redirect("/")
    return render_template(
        "results.html",
        result=session["result"]
    )

@app.route("/ping")
def ping():
    return {
        "status":"working",
        "model":MODEL,
        "keys_loaded":len(GROQ_KEYS)
    }

if __name__ == "__main__":
    app.run(
        debug=True
    )