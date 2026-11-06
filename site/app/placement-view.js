// Placement quiz view: ten questions on a track's start-here module, then a result
// that says whether to skip it, and the lessons to read if not.
import { shuffle } from "./interview.js";
import * as pl from "./placement.js";
import * as store from "./store.js";
import { fill, h } from "./ui.js";

function notFound(trackId) {
  return h("section", { class: "page" }, h("h1", {}, "Not found"), h("p", {}, `Track ${trackId} has no placement quiz.`), h("a", { href: "#/" }, "Back to dashboard"));
}

function lessonList(lessons) {
  return h("ul", { class: "plain-list review-lessons" }, lessons.map((l) => h("li", {}, h("a", { href: `#/lesson/${l.id}` }, `${l.id} ${l.title}`))));
}

// A short card for the module, track and dashboard pages: take the quiz, or see the last result.
export function placementCard(app, track, quiz) {
  const record = pl.placementFor(app.state, track.id);
  const start = quiz.module;
  if (!record) {
    return h("div", { class: "card placement-card" },
      h("strong", {}, `Already know ${start}?`),
      h("span", { class: "muted small" }, `Take the ${quiz.count}-question placement quiz. Score ${quiz.pass_mark} or more and you can skip ${start}.`),
      h("div", { class: "actions" }, h("a", { class: "btn secondary", href: `#/placement/${track.id}` }, "Take the placement quiz")),
    );
  }
  const verdict = record.skipped
    ? `You skipped ${start}.`
    : record.passed ? `You passed and can skip ${start}.` : `Start with ${start}.`;
  return h("div", { class: "card placement-card" },
    h("strong", {}, `Placement quiz: ${record.score} of ${record.total}`),
    h("span", { class: "muted small" }, `${record.day} · ${verdict}`),
    h("div", { class: "actions" },
      record.passed
        ? h("button", { type: "button", class: "btn secondary", onclick: () => {
            const skipped = pl.setSkipped(app.state, track.id, !record.skipped);
            app.save();
            app.toast(skipped ? `${start} skipped. Continue now passes over it.` : `${start} is back in your route.`);
            app.replaceState(app.state);
          } }, record.skipped ? `Undo: keep ${start}` : `Skip ${start}`)
        : null,
      h("a", { class: "btn ghost", href: `#/placement/${track.id}` }, "Retake"),
    ),
  );
}

export async function placementView(app, trackId) {
  const bank = await app.placement();
  const quiz = bank.quizzes.find((q) => q.track === trackId);
  if (!quiz) return notFound(trackId);
  const answers = {};
  const feedback = h("div", { class: "feedback", role: "status", "aria-live": "polite" });
  const result = h("div", { id: "placement-result" });
  const questions = quiz.questions.map((q, i) => {
    const options = shuffle(q.options, q.id);
    return h("li", { class: "placement-q", id: `pq-${q.id}` },
      h("div", { class: "prompt", html: q.question_html }),
      h("fieldset", { class: "choices" },
        h("legend", { class: "sr-only" }, `Question ${i + 1} options`),
        options.map((o) => h("label", { class: "choice", dataset: { option: o.id } },
          h("input", { type: "radio", name: `pq-${q.id}`, value: o.id, onchange: () => (answers[q.id] = o.id) }),
          h("span", { html: o.html }),
        )),
      ),
      h("div", { class: "placement-why", hidden: true }),
    );
  });
  const list = h("ol", { class: "placement-list" }, questions);

  const markQuestions = () => {
    quiz.questions.forEach((q, i) => {
      const item = questions[i];
      item.querySelector("fieldset").disabled = true;
      for (const label of item.querySelectorAll(".choice")) {
        const id = label.dataset.option;
        label.classList.toggle("right", id === q.answer);
        label.classList.toggle("wrong", id === answers[q.id] && id !== q.answer);
      }
      const why = item.querySelector(".placement-why");
      const ok = answers[q.id] === q.answer;
      fill(why,
        h("p", { class: `feedback ${ok ? "ok" : "bad"}` }, ok ? "Correct." : "Not quite."),
        h("div", { class: "explanation", html: q.explanation_html }),
        ok ? null : h("p", { class: "small" }, "Read: ", q.lessons.map((l, j) => [j ? ", " : "", h("a", { href: `#/lesson/${l.id}` }, `${l.id} ${l.title}`)])),
      );
      why.hidden = false;
    });
  };

  const showResult = (graded) => {
    const start = quiz.module;
    const after = quiz.next;
    const passedBox = [
      h("p", {}, `You can skip ${start.id} (${start.title}) and start at ${after.id} (${after.title}).`),
      graded.review.length ? [h("p", { class: "muted small" }, "Before you move on, skim the lessons behind the questions you missed:"), lessonList(graded.review)] : null,
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn", onclick: () => {
          pl.setSkipped(app.state, quiz.track, true);
          app.save();
          app.toast(`${start.id} skipped. Continue now passes over it.`);
          location.hash = `#/module/${after.id}`;
        } }, `Skip ${start.id} and go to ${after.id}`),
        h("a", { class: "btn ghost", href: `#/module/${start.id}` }, `Work through ${start.id} anyway`),
      ),
    ];
    const failedBox = [
      h("p", {}, `Start with ${start.id} (${start.title}). It is short, and every later module assumes it.`),
      h("p", { class: "muted small" }, "Focus on these lessons, where you missed questions:"),
      lessonList(graded.review),
      h("div", { class: "actions" },
        h("a", { class: "btn", href: `#/lesson/${graded.review[0]?.id ?? quiz.lessons[0].id}` }, "Start the first of them"),
        h("a", { class: "btn ghost", href: `#/module/${start.id}` }, `Open ${start.id}`),
      ),
    ];
    fill(result,
      h("h2", {}, "Your result"),
      h("p", { class: "drill-score" }, `${graded.score} of ${graded.total}`),
      h("p", { class: `feedback ${graded.passed ? "ok" : "info"}` }, graded.passed ? `Pass. The mark to skip is ${quiz.pass_mark}.` : `Below the mark of ${quiz.pass_mark}.`),
      graded.passed ? passedBox : failedBox,
      h("h2", {}, "Your answers"),
    );
  };

  const submit = h("button", { type: "button", class: "btn", onclick: () => {
    const left = pl.unanswered(quiz, answers);
    if (left) {
      feedback.className = "feedback info";
      fill(feedback, h("p", {}, `Answer every question first. ${left} left.`));
      return;
    }
    const graded = pl.gradeQuiz(quiz, answers);
    pl.recordPlacement(app.state, quiz, graded, store.today());
    store.markActive(app.state);
    app.save();
    fill(feedback);
    feedback.className = "feedback";
    submit.hidden = true;
    markQuestions();
    showResult(graded);
    list.before(result);
    result.scrollIntoView();
  } }, "See my result");

  return h(
    "section",
    { class: "page placement" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Dashboard"), " › ", h("a", { href: `#/track/${quiz.track}` }, `Track ${quiz.track}`)),
    h("h1", {}, `Placement quiz: ${quiz.track_title}`),
    h("p", {}, `Ten questions on ${quiz.module.id} (${quiz.module.title}). Score ${quiz.pass_mark} or more and you can skip it and start at ${quiz.next.id} (${quiz.next.title}). There is no clock.`),
    list,
    h("div", { class: "actions" }, submit),
    feedback,
  );
}
