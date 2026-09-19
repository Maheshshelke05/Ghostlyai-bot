import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import {
  type AuthOut,
  type NextStep,
  type StudentOut,
  fetchMe,
  signupWithResume as apiSignupWithResume,
  setAuthToken,
  setOnUnauthorized,
} from "@/lib/api";

const secureStorage: StateStorage = {
  getItem: async (name) => (await SecureStore.getItemAsync(name)) ?? null,
  setItem: async (name, value) => SecureStore.setItemAsync(name, value),
  removeItem: async (name) => SecureStore.deleteItemAsync(name),
};

interface AuthState {
  token: string | null;
  user: StudentOut | null;
  nextStep: NextStep | null;
  hydrated: boolean;
  signupWithResume: (
    file: { uri: string; name: string; mimeType?: string },
    fullName?: string
  ) => Promise<AuthOut>;
  commitAuth: (accessToken: string, me: { user: StudentOut; next_step: NextStep }) => void;
  logout: () => void;
  refreshMe: () => Promise<void>;
  applyMe: (me: { user: StudentOut; next_step: NextStep }) => void;
  setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      nextStep: null,
      hydrated: false,

      // Deliberately does NOT commit to the persisted store - the resume upload screen holds
      // the result while the "creating your profile" animation plays (and fills in a missing
      // phone number if needed), then calls commitAuth() once that's done. Committing here
      // would flip the root layout's Stack.Protected guards immediately, skipping the animation.
      signupWithResume: async (file, fullName) => {
        const result = await apiSignupWithResume(file, fullName);
        setAuthToken(result.access_token);
        return result;
      },

      commitAuth: (accessToken, me) => {
        setAuthToken(accessToken);
        set({ token: accessToken, user: me.user, nextStep: me.next_step });
      },

      logout: () => {
        setAuthToken(null);
        set({ token: null, user: null, nextStep: null });
      },

      refreshMe: async () => {
        if (!get().token) return;
        const me = await fetchMe();
        set({ user: me.user, nextStep: me.next_step });
      },

      applyMe: (me) => set({ user: me.user, nextStep: me.next_step }),

      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "jobkatta-auth",
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({ token: state.token, user: state.user, nextStep: state.nextStep }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.error("Auth rehydrate failed", error);
        if (state?.token) setAuthToken(state.token);
        state?.setHydrated();
      },
    }
  )
);

setOnUnauthorized(() => {
  useAuthStore.getState().logout();
});
