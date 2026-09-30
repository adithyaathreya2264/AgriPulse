// Toasts and confirm dialogs that any file can call (no hook needed).
// UIProvider (kit.js) registers the real handlers; without it (tests, storybook)
// the message goes to the console so nothing is lost.
const handlers = { toast: null, confirm: null };

export const registerNotifier = (toast, confirm) => {
  handlers.toast = toast;
  handlers.confirm = confirm;
};

// type: "info" | "success" | "error"
export const notify = (message, type = "info") => {
  if (handlers.toast) handlers.toast(message, type);
  else console.info(`[${type}]`, message);
};

export const confirmDialog = (message, options = {}) =>
  handlers.confirm ? handlers.confirm(message, options) : Promise.resolve(true);
