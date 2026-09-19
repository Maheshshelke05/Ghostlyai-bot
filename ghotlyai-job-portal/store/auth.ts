import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import {
  type AuthOut,
  type NextStep,
  type SignupOut,
  type StudentOut,
  fetchMe,
  login as apiLogin,
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
  ) => Promise<SignupOut>;
  login: (identifier: string, password: string) => Promise<AuthOut>;
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

      // Never issues a real access_token or touches the persisted store - resume upload alone
      // is not a login. The app either sets a password next (brand new / first app use) or is
      // told to go straight to Login (an account with a password already exists).
      signupWithResume: async (file, fullName) => {
        return await apiSignupWithResume(file, fullName);
      },

      // The one place a full access_token is actually issued. Committing it (below) is what
      // flips the root layout's Stack.Protected guards into (onboarding)/(tabs).
      login: async (identifier, password) => {
        const result = await apiLogin(identifier, password);
        get().commitAuth(result.access_token, { user: result.user, next_step: result.next_step });
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
