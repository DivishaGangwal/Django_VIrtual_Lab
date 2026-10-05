/**
 * Quiz client: collects answers, POSTs JSON to the server for grading and
 * shows per-question feedback. Correct answers are never sent to the browser
 * before submission.
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('quizForm');
  if (!form) return;
  const { notice, fetchJSON, csrfToken } = LabUtils;
  const submitBtn = document.getElementById('quizSubmitBtn');
  const retryBtn = document.getElementById('quizRetryBtn');
  const questions = [...form.querySelectorAll('.quiz-question')];

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const answers = {};
    questions.forEach(q => {
      const checked = q.querySelector('input[type=radio]:checked');
      if (checked) answers[q.dataset.qid] = Number(checked.value);
    });
    const unanswered = questions.length - Object.keys(answers).length;
    if (unanswered > 0) {
      notice(document.getElementById('quizNotice'), 'error', '⚠️ Incomplete', `Please answer all questions (${unanswered} left).`);
      questions.find(q => !q.querySelector('input:checked'))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    submitBtn.disabled = true;
    try {
      const { ok, data } = await fetchJSON(form.dataset.submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ student_name: document.getElementById('studentName').value, answers }),
      });
      if (!ok || data.status !== 'success') throw new Error(data.message || 'Grading failed');

      document.getElementById('quizNotice').replaceChildren();
      data.results.forEach(r => {
        const q = form.querySelector(`.quiz-question[data-qid="${r.id}"]`);
        q.querySelectorAll('.quiz-option').forEach(opt => {
          const idx = Number(opt.dataset.index);
          opt.classList.toggle('correct', idx === r.correct_option);
          opt.classList.toggle('wrong', idx === r.chosen && !r.is_correct);
          opt.querySelector('input').disabled = true;
        });
        const exp = q.querySelector('.quiz-explanation');
        exp.textContent = (r.is_correct ? '✓ Correct. ' : '✗ Incorrect. ') + r.explanation;
        exp.classList.remove('is-hidden');
      });

      document.getElementById('quizScore').textContent = `${data.score}/${data.total}`;
      document.getElementById('quizScoreText').textContent =
        `${data.percentage}% — ${data.percentage >= 80 ? 'Excellent work!' : data.percentage >= 50 ? 'Good effort — review the explanations above.' : 'Revisit the Theory page and try again.'} (Attempt #${data.attempt_id} saved)`;
      document.getElementById('quizResult').classList.remove('is-hidden');
      document.getElementById('quizResult').scrollIntoView({ behavior: 'smooth' });
      submitBtn.classList.add('is-hidden');
      retryBtn.classList.remove('is-hidden');
    } catch (err) {
      notice(document.getElementById('quizNotice'), 'error', '⚠️ Could not submit', err.message);
      submitBtn.disabled = false;
    }
  });

  retryBtn.addEventListener('click', () => window.location.reload());
});
