const quizState = {
  questions: [],
  answers: {},
  review: {},
  current: 0,
  timer: null,
};

const examTitle = document.getElementById("examTitle");
const timerElement = document.getElementById("timer");
const difficultyBadge = document.getElementById("difficultyBadge");
const questionCounter = document.getElementById("questionCounter");
const questionNumber = document.getElementById("questionNumber");
const questionText = document.getElementById("questionText");
const optionsContainer = document.getElementById("optionsContainer");
const progressBar = document.getElementById("progressBar");
const progressPercent = document.getElementById("progressPercent");
const palette = document.getElementById("questionPalette");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const reviewBtn = document.getElementById("reviewBtn");
const submitBtn = document.getElementById("submitBtn");
const footerSubmitBtn = document.getElementById("footerSubmitBtn");

submitBtn.onclick = openSubmitModal;
footerSubmitBtn.onclick = openSubmitModal;

const modal = document.getElementById("submit-modal");
const confirmBtn = document.getElementById("confirmSubmitBtn");

function openSubmitModal() {
  modal.classList.remove("hidden");
}

const cancelBtn = document.getElementById("cancelSubmitBtn");

cancelBtn.onclick = function () {
  modal.classList.add("hidden");
};

confirmBtn.onclick = function () {
    modal.classList.add("hidden");
    submitExam();
}

async function loadQuestions() {
  try {
    const response = await fetch("/questions");
    const result = await response.json();
    console.log(result);
    if (!result.success) {
      alert(result.message);
      window.location = "/";
      return;
    }
    startTimer(result.data.duration);
    quizState.questions = result.data.questions;
    examTitle.textContent = result.data.topic;
    difficultyBadge.textContent = result.data.difficulty;
    renderPalette();
    renderQuestion();
  } catch (err) {
    console.error(err);
    alert(err.message);
  }
}

function renderQuestion() {
  const q = quizState.questions[quizState.current];

  if (!q) return;
  questionNumber.textContent = `Question ${quizState.current + 1}`;
  questionCounter.textContent = `Question ${quizState.current + 1} of ${quizState.questions.length}`;
  questionText.textContent = q.question;
  renderOptions(q);
  updateProgress();
  prevBtn.disabled = quizState.current === 0;
  nextBtn.disabled = quizState.current === quizState.questions.length - 1;
  renderPalette();
}

function renderPalette() {
  palette.innerHTML = "";
  quizState.questions.forEach((q, index) => {
    const btn = document.createElement("button");
    btn.textContent = index + 1;
    btn.className =
      "w-10 h-10 rounded-lg border text-sm font-semibold transition-all";
    if (index === quizState.current) {
      btn.classList.add("bg-primary", "text-white");
    } else if (quizState.review[index]) {
      btn.classList.add("bg-yellow-400", "text-black");
    } else if (quizState.answers[index]) {
      btn.classList.add("bg-green-600", "text-white");
    } else {
      btn.classList.add("bg-white", "border");
    }
    btn.onclick = function () {
      quizState.current = index;
      renderQuestion();
    };
    palette.appendChild(btn);
  });
}

function renderOptions(question) {
  optionsContainer.innerHTML = "";
  const letters = ["A", "B", "C", "D"];
  const selected = quizState.answers[quizState.current];
  question.options.forEach((option, index) => {
    const letter = letters[index];
    const label = document.createElement("label");
    let classes =
      "group relative flex items-center p-md rounded-xl cursor-pointer transition-all duration-200 border ";
    if (selected === letter) {
      classes += "border-2 border-primary bg-primary-fixed";
    } else {
      classes +=
        "border-outline-variant hover:border-primary hover:bg-surface-container-low";
    }
    label.className = classes;
    label.innerHTML = `
<input
type="radio"
name="quiz_option"
class="hidden"
${selected === letter ? "checked" : ""}
>
<div
class="w-10 h-10 rounded-lg flex items-center justify-center font-bold
${
  selected === letter
    ? "bg-primary text-white"
    : "bg-surface-container-highest text-on-surface-variant"
}">
${letter}
</div>
<span class="ml-md flex-1 font-body-lg">
${option}
</span>
${
  selected === letter
    ? `<span class="material-symbols-outlined text-primary">
check_circle
</span>`
    : ""
}

`;
    label.addEventListener("click", () => {
      saveAnswer(letter);
      renderQuestion();
    });
    optionsContainer.appendChild(label);
  });
}

reviewBtn.addEventListener("click", function () {
  quizState.review[quizState.current] = true;
  if (quizState.current < quizState.questions.length - 1) {
    quizState.current++;
  }
  renderQuestion();
});

function saveAnswer(letter) {
  quizState.answers[quizState.current] = letter;
  updateProgress();
  renderPalette();
}

let countdown;

function startTimer(seconds) {
  quizState.timer = seconds;
  updateTimer();
  countdown = setInterval(function () {
    quizState.timer--;
    updateTimer();
    if (quizState.timer <= 0) {
      clearInterval(countdown);
      submitExam();
    }
  }, 1000);
}

function updateTimer() {
  const min = Math.floor(quizState.timer / 60);
  const sec = quizState.timer % 60;
  timerElement.textContent = `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

let submitted = false;

async function submitExam() {
    if (submitted) return;
    submitted = true;
    clearInterval(countdown);
    const response = await fetch("/submit", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            answers: quizState.answers,
        }),
    });
    const result = await response.json();
    window.location = result.data.redirect;
}

nextBtn.addEventListener("click", function () {
  if (quizState.current < quizState.questions.length - 1) {
    quizState.current++;
    renderQuestion();
  }
});

prevBtn.addEventListener("click", function () {
  if (quizState.current > 0) {
    quizState.current--;
    renderQuestion();
  }
});

function updateProgress() {
  const attempted = Object.keys(quizState.answers).length;
  const percent = Math.round((attempted / quizState.questions.length) * 100);
  progressBar.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
}

document.addEventListener("DOMContentLoaded", function () {
  loadQuestions();
});
