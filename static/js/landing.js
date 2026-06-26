const form = document.getElementById("generator-form");
const loading = document.getElementById("loading-state");
const submitBtn = document.getElementById("submit-btn");
const examCard = document.getElementById("exam-card");

function showLoading() {
  form.classList.add("hidden");
  loading.classList.remove("hidden");
  submitBtn.disabled = true;
}
function hideLoading() {
  loading.classList.add("hidden");
  form.classList.remove("hidden");
  submitBtn.disabled = false;
}

function validateForm() {
  const topic = document.getElementById("topic").value.trim();
  if (topic === "") {
    alert("Please enter a topic.");
    return false;
  }
  return true;
}

function getFormData() {
  return {
    topic: document.getElementById("topic").value.trim(),
    subtopic: document.getElementById("subtopic").value.trim(),
    difficulty: document.getElementById("difficulty").value,
    questions: parseInt(document.getElementById("questionCount").value),
  };
}

form.addEventListener("submit", async function (e) {
  e.preventDefault();
  if (!validateForm()) return;
  showLoading();
  const data = getFormData();
  data.duration = document.getElementById("examTime").value;
  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    const result = await response.json();
    if (result.success) {
      window.location = result.data.redirect;
    } else {
      hideLoading();
      alert(result.message);
    }
  } catch (error) {
    hideLoading();
    console.error(error);
    alert("Unable to connect to server.");
  }
});
