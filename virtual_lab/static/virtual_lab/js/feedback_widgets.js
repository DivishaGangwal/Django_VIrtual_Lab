/**
 * Header "Rate me" / "Report bug" modals and the Step 9 Feedback form.
 * Each form is checked here for quick feedback, then POSTed as JSON (with the
 * CSRF token) to a Django API that validates it again and saves a model row.
 * Results are shown as toasts; all text is set with textContent.
 */
document.addEventListener('DOMContentLoaded', () => {
  const { el, postJSON, toast } = LabUtils;

  function showFormError(form, message) {
    const box = form.querySelector('.form-error');
    if (!box) return;
    box.textContent = message ? `✗ ${message}` : '';
    box.classList.toggle('is-hidden', !message);
  }

  /** Validates with `check` (returns an error string or ''), POSTs, then calls onSuccess(data). */
  function wireForm(form, { collect, check, onSuccess, failTitle }) {
    if (!form) return;
    form.addEventListener('change', () => showFormError(form, ''));
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = collect();
      const problem = check(payload);
      if (problem) { showFormError(form, problem); return; }
      showFormError(form, '');
      const submitBtn = form.querySelector('[type=submit]');
      submitBtn.disabled = true;
      try {
        const { ok, data } = await postJSON(form.dataset.url, payload);
        if (!ok || data.status !== 'success') throw new Error(data.message || 'The server rejected the form.');
        onSuccess(data);
      } catch (err) {
        showFormError(form, err.message);
        toast('error', `${failTitle}: ${err.message}`);
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  const checkedValue = (form, name) => form.querySelector(`input[name="${name}"]:checked`)?.value || '';
  const hideModal = (form) => {
    const modal = form.closest('.modal');
    if (modal && window.bootstrap) bootstrap.Modal.getOrCreateInstance(modal).hide();
  };

  /* ---------- Rate me ---------- */
  function renderAverage(summary) {
    const box = document.getElementById('ratingAverage');
    if (!box) return;
    if (summary.average === null || summary.average === undefined) {
      box.replaceChildren('No ratings yet');
      return;
    }
    box.replaceChildren(
      el('span', { class: 'vl-rating-star', 'aria-hidden': 'true', text: '★' }),
      ` ${Number(summary.average).toFixed(1)}`,
      el('span', { class: 'vl-rating-count', text: ` (${summary.count})` }),
    );
  }

  const rateForm = document.getElementById('rateForm');
  wireForm(rateForm, {
    collect: () => ({ stars: Number(checkedValue(rateForm, 'stars')) || null, comment: rateForm.querySelector('[name=comment]').value }),
    check: (p) => (p.stars ? '' : 'Choose between 1 and 5 stars.'),
    failTitle: 'Rating not saved',
    onSuccess: (data) => {
      renderAverage(data.summary);
      hideModal(rateForm);
      toast('success', data.created ? `Thanks! Your ${data.stars}★ rating was saved.` : `Your rating was updated to ${data.stars}★.`);
    },
  });

  /* ---------- Report bug ---------- */
  const bugForm = document.getElementById('bugForm');
  wireForm(bugForm, {
    collect: () => ({
      issue_types: [...bugForm.querySelectorAll('input[name=issue_types]:checked')].map(i => i.value),
      description: bugForm.querySelector('[name=description]').value.trim(),
      page_name: bugForm.querySelector('[name=page_name]').value.trim(),
    }),
    check: (p) => (!p.issue_types.length ? 'Tick at least one type of issue.'
      : p.description.length < 5 ? 'Please describe the problem in a few words.' : ''),
    failTitle: 'Bug report not sent',
    onSuccess: (data) => {
      bugForm.querySelectorAll('input[name=issue_types]').forEach(i => { i.checked = false; });
      bugForm.querySelector('[name=description]').value = '';
      hideModal(bugForm);
      toast('success', `Bug report #${data.report_id} sent. Thank you!`);
    },
  });

  /* ---------- Step 9: Feedback page ---------- */
  const feedbackForm = document.getElementById('feedbackForm');
  wireForm(feedbackForm, {
    collect: () => ({
      name: feedbackForm.querySelector('[name=name]').value.trim(),
      overall_rating: Number(checkedValue(feedbackForm, 'overall_rating')) || null,
      most_useful: feedbackForm.querySelector('[name=most_useful]').value.trim(),
      to_improve: feedbackForm.querySelector('[name=to_improve]').value.trim(),
      would_recommend: checkedValue(feedbackForm, 'would_recommend'),
    }),
    check: (p) => (!p.overall_rating ? 'Choose an overall rating (1 to 5 stars).'
      : !p.would_recommend ? 'Tell us whether you would recommend this lab.' : ''),
    failTitle: 'Feedback not saved',
    onSuccess: () => {
      feedbackForm.classList.add('is-hidden');
      const thanks = document.getElementById('feedbackThanks');
      thanks.classList.remove('is-hidden');
      thanks.scrollIntoView({ behavior: 'smooth', block: 'center' });
      toast('success', 'Feedback saved. Thank you!');
    },
  });
});
