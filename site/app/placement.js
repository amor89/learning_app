// Placement quiz logic: grade ten answers, decide whether to skip the start-here
// module, and record the result. Pure functions, so Node can test them.

export function gradeQuiz(quiz, answers) {
  const missed = quiz.questions.filter((q) => answers[q.id] !== q.answer);
  const score = quiz.questions.length - missed.length;
  const wrongLessons = new Set(missed.flatMap((q) => q.lessons.map((l) => l.id)));
  return {
    score,
    total: quiz.questions.length,
    passed: score >= quiz.pass_mark,
    missed: missed.map((q) => q.id),
    review: quiz.lessons.filter((l) => wrongLessons.has(l.id)),
  };
}

export function unanswered(quiz, answers) {
  return quiz.questions.filter((q) => !answers[q.id]).length;
}

// The position of the first question without an answer, or -1 when all have one.
export function firstUnanswered(quiz, answers) {
  return quiz.questions.findIndex((q) => !answers[q.id]);
}

// Keeps the latest result per track. A retake clears an earlier skip until you choose again.
export function recordPlacement(state, quiz, result, day) {
  state.placement ??= {};
  state.placement[quiz.track] = {
    module: quiz.module.id,
    day,
    score: result.score,
    total: result.total,
    passed: result.passed,
    review: result.review.map((l) => l.id),
    skipped: false,
  };
  return state.placement[quiz.track];
}

// Only a passed quiz lets you skip.
export function setSkipped(state, track, skipped) {
  const record = state.placement?.[track];
  if (!record) return false;
  record.skipped = Boolean(skipped && record.passed);
  return record.skipped;
}

export function placementFor(state, track) {
  return state.placement?.[track] ?? null;
}
