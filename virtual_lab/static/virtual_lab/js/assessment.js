/**
 * Pretest / Posttest client.
 *  - "Choose difficulty" checkboxes show/hide each level's questions; at least
 *    one level always stays selected.
 *  - Collects answers for the visible questions only and POSTs them as JSON
 *    with the chosen levels. The server grades them (answers never reach the
 *    browser before submission) and returns per-question feedback.
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('assessmentForm');
  if (!form) return;
  const { notice, postJSON } = LabUtils;
  const LETTERS = ['A', 'B', 'C', 'D'];
  const submitBtn = document.getElementById('quizSubmitBtn');
  const retryBtn = document.getElementById('quizRetryBtn');
  const noticeBox = document.getElementById('quizNotice');
  const hint = document.getElementById('difficultyHint');
  const levelBoxes = [...form.querySelectorAll('input[name=levels]')];
  const sections = [...form.querySelectorAll('.assessment-level')];

  const selectedLevels = () => levelBoxes.filter(b => b.checked).map(b => b.value);
  const visibleQuestions = () => sections.filter(s => !s.classList.contains('is-hidden'))
    .flatMap(s => [...s.querySelectorAll('.quiz-question')]);

  function syncLevels() {
    const chosen = selectedLevels();
    sections.forEach(s => s.classList.toggle('is-hidden', !chosen.includes(s.dataset.level)));
  }

  levelBoxes.forEach(box => box.addEventListener('change', () => {
    if (!selectedLevels().length) {
      box.checked = true; // keep at least one level selected
      hint.textContent = 'At least one difficulty level must stay selected.';
      hint.classList.add('field-hint-warn');
    } else {
      hint.textContent = 'Tick a level to show its questions. At least one level stays selected.';
      hint.classList.remove('field-hint-warn');
    }
    noticeBox.replaceChildren();
    syncLevels();
  }));
  syncLevels(); // respects checkboxes restored by the browser on back/forward

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const questions = visibleQuestions();
    const answers = {};
    questions.forEach(q => {
      const checked = q.querySelector('input[type=radio]:checked');
      if (checked) answers[q.dataset.qid] = Number(checked.value);
    });
    const unanswered = questions.length - Object.keys(answers).length;
    if (unanswered > 0) {
      notice(noticeBox, 'error', '⚠️ Incomplete', `Please answer all visible questions (${unanswered} left).`);
      questions.find(q => !q.querySelector('input:checked'))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    submitBtn.disabled = true;
    try {
      const { ok, data } = await postJSON(form.dataset.submitUrl, {
        test_type: form.dataset.testType,
        levels: selectedLevels(),
        student_name: document.getElementById('studentName').value,
        answers,
      });
      if (!ok || data.status !== 'success') throw new Error(data.message || 'Grading failed');

      noticeBox.replaceChildren();
      levelBoxes.forEach(b => { b.disabled = true; });
      data.results.forEach(r => {
        const q = form.querySelector(`.quiz-question[data-qid="${r.id}"]`);
        if (!q) return;
        q.querySelectorAll('.quiz-option').forEach(opt => {
          const idx = Number(opt.dataset.index);
          opt.classList.toggle('correct', idx === r.correct_option);
          opt.classList.toggle('wrong', idx === r.chosen && !r.is_correct);
          opt.querySelector('input').disabled = true;
        });
        const exp = q.querySelector('.quiz-explanation');
        exp.textContent = r.is_correct
          ? `✓ Correct. ${r.explanation}`
          : `✗ Incorrect. The correct answer is ${LETTERS[r.correct_option]}. ${r.explanation}`;
        exp.classList.toggle('is-correct', r.is_correct);
        exp.classList.toggle('is-wrong', !r.is_correct);
        exp.classList.remove('is-hidden');
      });

      const levelNames = data.levels.map(l => l[0].toUpperCase() + l.slice(1)).join(', ');
      document.getElementById('quizScore').textContent = `${data.score}/${data.total}`;
      document.getElementById('quizScoreText').textContent =
        `${data.percentage}% (${levelNames}): ${data.percentage >= 80 ? 'Excellent work!' : data.percentage >= 50 ? 'Good effort. Review the explanations above.' : 'Revisit the Theory page and try again.'} Attempt #${data.attempt_id} saved.`;
      const result = document.getElementById('quizResult');
      result.classList.remove('is-hidden');
      result.scrollIntoView({ behavior: 'smooth' });
      submitBtn.classList.add('is-hidden');
      retryBtn.classList.remove('is-hidden');
    } catch (err) {
      notice(noticeBox, 'error', '⚠️ Could not submit', err.message);
      submitBtn.disabled = false;
    }
  });

  retryBtn.addEventListener('click', () => window.location.reload());
});
