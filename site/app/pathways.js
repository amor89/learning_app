// Pathway logic: which pathway is chosen, how far each stage is, and the next lesson.
// Pure functions over the content index and the progress state, so Node can test them.
import * as store from "./store.js";

export function moduleIndex(index) {
  const byId = new Map();
  for (const track of index.tracks) {
    for (const module of track.modules) byId.set(module.id, { ...module, track });
  }
  return byId;
}

export function chosenPathway(index, state) {
  const wanted = state.settings.pathway;
  return index.pathways.find((p) => p.id === wanted) ?? index.pathways[0];
}

export function choosePathway(state, pathwayId) {
  state.settings.pathway = pathwayId;
}

export function stageModules(stage, modules) {
  return stage.modules.map((id) => modules.get(id)).filter(Boolean);
}

export function stageProgress(state, stage, modules) {
  const ids = stageModules(stage, modules).flatMap(store.moduleExercises);
  const done = ids.filter((id) => store.isDone(state, id)).length;
  return { done, total: ids.length, share: ids.length ? done / ids.length : 0 };
}

export function pathwayProgress(state, pathway, modules) {
  const parts = pathway.stages.map((s) => stageProgress(state, s, modules));
  const done = parts.reduce((n, p) => n + p.done, 0);
  const total = parts.reduce((n, p) => n + p.total, 0);
  return { done, total, share: total ? done / total : 0 };
}

// The first unfinished lesson in pathway order, with its stage and module.
// Modules skipped after a placement quiz are passed over.
export function nextStep(state, pathway, modules) {
  const skipped = store.skippedModules(state);
  for (const stage of pathway.stages) {
    for (const module of stageModules(stage, modules)) {
      if (skipped.has(module.id)) continue;
      const lesson = module.lessons.find((l) => !store.lessonComplete(state, l));
      if (lesson) return { stage, module, lesson };
    }
  }
  return null;
}

// The stage holding the next step, or the last stage once everything is done.
export function currentStageId(state, pathway, modules) {
  return nextStep(state, pathway, modules)?.stage.id ?? pathway.stages.at(-1).id;
}

// Every published lesson of a pathway, in order, each with its stage and module.
export function pathwayLessons(pathway, modules) {
  return pathway.stages.flatMap((stage) =>
    stageModules(stage, modules).flatMap((module) => module.lessons.map((lesson) => ({ stage, module, lesson }))),
  );
}

// The lesson that follows lessonId in the pathway, or null at the end or when it is not in the pathway.
export function followingLesson(pathway, modules, lessonId) {
  const order = pathwayLessons(pathway, modules);
  const at = order.findIndex((step) => step.lesson.id === lessonId);
  return at === -1 ? null : order[at + 1] ?? null;
}
