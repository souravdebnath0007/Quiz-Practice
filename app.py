import os
import json
import random
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

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
    prompt = f"""
Generate exactly {number_of_questions} Multiple Choice Questions.
Topic:
{topic}
Subtopic:
{subtopic}
Difficulty:
{difficulty}
Return ONLY JSON.
Format:
[
    {{
        "question":"",
        "options":[
            "",
            "",
            "",
            ""
        ],
        "correct":"A",
        "discussion":""
    }}
]
"""
    return prompt

def validate_questions(questions):
    valid = []
    for q in questions:
        if (
            "question" in q and
            "options" in q and
            "correct" in q and
            "discussion" in q
        ):
            if len(q["options"]) == 4:
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
        difficulty_time = {
            "Easy": 90,
            "Medium": 60,
            "Hard": 30
        }

        per_question = difficulty_time.get(difficulty,60)

        session["exam_meta"]={
            "topic":topic,
            "difficulty":difficulty,
            "total":number,
            "duration":number*per_question
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