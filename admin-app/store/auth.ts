import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

import { type AdminOut, fetchMe, login as apiLogin, setAuthToken, setOnUnauthorized } from "@/lib/api";

const secureStorage: StateStorage = {
  getItem: async (name) => (await SecureStore.getItemAsync(name)) ?? null,
  setItem: async (name, value) => SecureStore.setItemAsync(name, value),
  removeItem: async (name) => SecureStore.deleteItemAsync(name),
};

interface AuthState {
  token: string | null;
  admin: AdminOut | null;
  hydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
  setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      admin: null,
      hydrated: false,

      login: async (email, password) => {
        const { access_token, admin } = await apiLogin(email, password);
        setAuthToken(access_token);
        set({ token: access_token, admin });
      },

      logout: () => {
        setAuthToken(null);
        set({ token: null, admin: null });
      },

      refreshMe: async () => {
        if (!get().token) return;
        const admin = await fetchMe();
        set({ admin });
      },

      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "job-alert-admin-auth",
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({ token: state.token, admin: state.admin }),
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

export const useIsOwner = () => useAuthStore((s) => s.admin?.role === "owner");
