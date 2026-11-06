// Navigation helpers for the page header: where Back goes, and which pages are tab roots.

// The five tab pages. They have no Back button.
export const ROOT_HASHES = ["", "#", "#/", "#/paths", "#/interview", "#/review", "#/settings"];

export function isRoot(hash) {
  return ROOT_HASHES.includes(hash ?? "");
}

// The pages visited in this session, newest last. Returning to the page before the
// current one counts as Back and pops the stack. Any other visit pushes.
export function visit(stack, hash) {
  if (stack.at(-1) === hash) return stack;
  if (stack.length > 1 && stack.at(-2) === hash) return stack.slice(0, -1);
  return [...stack, hash];
}

// "history" when the app has a page to go back to, otherwise the parent page:
// the last breadcrumb link, or Home. A home-screen app opened on a deep link has no
// history, so Back must still lead somewhere.
export function backTarget(stack, parentHref) {
  if (stack.length > 1) return "history";
  return parentHref || "#/";
}
