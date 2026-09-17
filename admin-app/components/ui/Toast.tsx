import { AnimatePresence, MotiView } from "moti";
import { createContext, useCallback, useContext, useRef, useState } from "react";
import { Text } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

type ToastKind = "success" | "warn" | "error";

interface ToastMessage {
  id: number;
  text: string;
  kind: ToastKind;
}

interface ToastContextValue {
  show: (text: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const KIND_CLASSES: Record<ToastKind, string> = {
  success: "bg-go",
  warn: "bg-brand",
  error: "bg-danger",
};

const KIND_TEXT: Record<ToastKind, string> = {
  success: "text-white",
  warn: "text-brand-ink",
  error: "text-white",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  // Two events (e.g. a new signup and a new support message) can land in the same poll tick -
  // a queue means the second one still gets its own moment on screen instead of being silently
  // overwritten by the first show() call. `active` is a ref (not state) so show() can check
  // "is something on screen right now" synchronously, with no state-batching surprises.
  const queue = useRef<ToastMessage[]>([]);
  const active = useRef(false);
  const nextId = useRef(0);
  const insets = useSafeAreaInsets();

  const advance = useCallback(() => {
    const next = queue.current.shift();
    if (next) {
      active.current = true;
      setToast(next);
      setTimeout(advance, 2500);
    } else {
      active.current = false;
      setToast(null);
    }
  }, []);

  const show = useCallback(
    (text: string, kind: ToastKind = "success") => {
      const message = { id: ++nextId.current, text, kind };
      if (active.current) {
        queue.current.push(message);
        return;
      }
      active.current = true;
      setToast(message);
      setTimeout(advance, 2500);
    },
    [advance]
  );

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <AnimatePresence>
        {toast ? (
          <MotiView
            key={toast.id}
            from={{ translateY: -60, opacity: 0 }}
            animate={{ translateY: 0, opacity: 1 }}
            exit={{ translateY: -60, opacity: 0 }}
            transition={{ type: "timing", duration: 220 }}
            className={`absolute left-4 right-4 rounded-2xl px-4 py-3 ${KIND_CLASSES[toast.kind]}`}
            style={{ top: insets.top + 8, zIndex: 100 }}
          >
            <Text className={`text-sm font-semibold ${KIND_TEXT[toast.kind]}`}>{toast.text}</Text>
          </MotiView>
        ) : null}
      </AnimatePresence>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
