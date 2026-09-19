import { create } from "zustand";

import type { JobType, SignupOut } from "@/lib/api";

/** In-memory only (not persisted) - holds the resume -> job-types -> categories sub-flow's
 * picks until they're all submitted together via POST /student/me/complete, mirroring how the
 * Telegram bot's FSM only commits categories+job_types at the very end of onboarding.
 *
 * Also stages handoffs across the (auth) screens, none of which touch the persisted auth store:
 * the name typed before the resume is even uploaded, the signup API result while the "creating
 * your profile" animation plays, and the phone/email to prefill on the Login screen once a
 * password has been set (see store/auth.ts::signupWithResume/login/commitAuth). */
interface OnboardingDraftState {
  suggestedCategorySlugs: string[];
  selectedJobTypes: JobType[];
  selectedCategoryIds: number[];
  pendingName: string;
  pendingSignup: SignupOut | null;
  loginPrefill: string;
  setSuggestedCategorySlugs: (slugs: string[]) => void;
  toggleJobType: (jt: JobType) => void;
  toggleCategory: (id: number, max: number) => boolean;
  setPendingName: (name: string) => void;
  setPendingSignup: (signup: SignupOut | null) => void;
  setLoginPrefill: (identifier: string) => void;
  reset: () => void;
}

export const useOnboardingDraft = create<OnboardingDraftState>()((set, get) => ({
  suggestedCategorySlugs: [],
  selectedJobTypes: [],
  selectedCategoryIds: [],
  pendingName: "",
  pendingSignup: null,
  loginPrefill: "",

  setSuggestedCategorySlugs: (slugs) => set({ suggestedCategorySlugs: slugs }),
  setPendingName: (name) => set({ pendingName: name }),
  setPendingSignup: (signup) => set({ pendingSignup: signup }),
  setLoginPrefill: (identifier) => set({ loginPrefill: identifier }),

  toggleJobType: (jt) => {
    const current = get().selectedJobTypes;
    set({
      selectedJobTypes: current.includes(jt) ? current.filter((x) => x !== jt) : [...current, jt],
    });
  },

  /** Returns false (and leaves state unchanged) if adding a new selection would exceed `max`. */
  toggleCategory: (id, max) => {
    const current = get().selectedCategoryIds;
    if (current.includes(id)) {
      set({ selectedCategoryIds: current.filter((x) => x !== id) });
      return true;
    }
    if (current.length >= max) return false;
    set({ selectedCategoryIds: [...current, id] });
    return true;
  },

  reset: () =>
    set({
      suggestedCategorySlugs: [],
      selectedJobTypes: [],
      selectedCategoryIds: [],
      pendingName: "",
      pendingSignup: null,
      loginPrefill: "",
    }),
}));
