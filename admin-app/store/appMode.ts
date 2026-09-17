import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

export type AppMode = "jobalert" | "ghostly";

const secureStorage: StateStorage = {
  getItem: async (name) => (await SecureStore.getItemAsync(name)) ?? null,
  setItem: async (name, value) => SecureStore.setItemAsync(name, value),
  removeItem: async (name) => SecureStore.deleteItemAsync(name),
};

interface AppModeState {
  mode: AppMode;
  hydrated: boolean;
  /** Non-null while the branded switch-workspace overlay is showing; the target it's headed to. */
  switchingTo: AppMode | null;
  setMode: (mode: AppMode) => void;
  /** Shows the full-screen transition, then flips `mode` once it finishes (see
   * WorkspaceSwitchOverlay). This is what every "switch workspace" button should call instead
   * of setMode directly, so the transition is consistent everywhere it's triggered from. */
  beginSwitch: (mode: AppMode) => void;
  endSwitch: () => void;
  setHydrated: () => void;
}

/** Which "workspace" the app is showing: the Job Alert Bot admin panel, or the GhostlyAI.in
 * one (Settings > Switch to GhotlyAI.in). Persisted so the app reopens into the same mode. */
export const useAppModeStore = create<AppModeState>()(
  persist(
    (set, get) => ({
      mode: "jobalert",
      hydrated: false,
      switchingTo: null,
      setMode: (mode) => set({ mode }),
      beginSwitch: (mode) => {
        if (get().mode === mode || get().switchingTo) return;
        set({ switchingTo: mode });
      },
      endSwitch: () => {
        const target = get().switchingTo;
        if (!target) return;
        set({ mode: target, switchingTo: null });
      },
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "job-alert-admin-app-mode",
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({ mode: state.mode }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.error("App-mode rehydrate failed", error);
        state?.setHydrated();
      },
    }
  )
);

export const useAppMode = () => useAppModeStore((s) => s.mode);
