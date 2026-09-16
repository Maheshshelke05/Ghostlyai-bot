// React's own ErrorBoundary only catches errors thrown during render. A crash
// inside an async function, a Promise, or an event handler (the most common
// real-world crash source) skips right past it and the user just sees the
// native "app has stopped" dialog with zero detail. This hooks into RN's
// global handler so ANY fatal JS error - render or not - gets captured with
// its full message + stack, so a user can screenshot/copy it instead of just
// saying "it crashed."
type Listener = (error: Error, isFatal: boolean) => void;

let listener: Listener | null = null;
let installed = false;

export function onCrash(cb: Listener) {
  listener = cb;
}

export function installCrashHandler() {
  if (installed) return;
  installed = true;

  const g = globalThis as unknown as {
    ErrorUtils?: { setGlobalHandler: (fn: Listener) => void; getGlobalHandler?: () => Listener };
  };
  if (!g.ErrorUtils) return;

  const previousHandler = g.ErrorUtils.getGlobalHandler?.();

  g.ErrorUtils.setGlobalHandler((error, isFatal) => {
    listener?.(error, isFatal);
    previousHandler?.(error, isFatal);
  });
}
