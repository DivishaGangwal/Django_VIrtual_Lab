/**
 * Virtual Lab Navigator Controller
 * Manages active step indicators, progress completion, and linear navigation flow.
 */

document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;

  // Determine current step index from current URL
  const stepMap = {
    '/': 1,
    '/theory/': 2,
    '/procedure/': 3,
    '/simulation/': 4,
    '/observations/': 5,
    '/quiz/': 6
  };

  let activeStep = 1;
  for (const [path, stepNum] of Object.entries(stepMap)) {
    if (currentPath.endsWith(path) || currentPath === path) {
      activeStep = stepNum;
      break;
    }
  }

  // Update step ribbons if needed
  const stepItems = document.querySelectorAll('.lab-step-item');
  stepItems.forEach((item, index) => {
    const stepIndex = index + 1;
    if (stepIndex < activeStep) {
      item.classList.add('completed');
      item.classList.remove('active', 'pulse-active');
    } else if (stepIndex === activeStep) {
      item.classList.add('active', 'pulse-active');
      item.classList.remove('completed');
    } else {
      item.classList.remove('active', 'completed', 'pulse-active');
    }
  });
});
