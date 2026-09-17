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
  setMode: (mode: AppMode) => void;
  setHydrated: () => void;
}

/** Which "workspace" the app is showing: the Job Alert Bot admin panel, or the GhostlyAI.in
 * one (Settings > Switch to GhotlyAI.in). Persisted so the app reopens into the same mode. */
export const useAppModeStore = create<AppModeState>()(
  persist(
    (set) => ({
      mode: "jobalert",
      hydrated: false,
      setMode: (mode) => set({ mode }),
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
