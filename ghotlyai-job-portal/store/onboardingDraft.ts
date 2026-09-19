import { create } from "zustand";

import type { AuthOut, JobType } from "@/lib/api";

/** In-memory only (not persisted) - holds the resume -> job-types -> categories sub-flow's
 * picks until they're all submitted together via POST /student/me/complete, mirroring how the
 * Telegram bot's FSM only commits categories+job_types at the very end of onboarding.
 *
 * Also stages two pre-login handoffs across the (auth) screens: the name typed before the
 * resume is even uploaded, and the signup API result while the "creating your profile"
 * animation plays (see store/auth.ts::signupWithResume/commitAuth). */
interface OnboardingDraftState {
  suggestedCategorySlugs: string[];
  selectedJobTypes: JobType[];
  selectedCategoryIds: number[];
  pendingName: string;
  pendingAuth: AuthOut | null;
  setSuggestedCategorySlugs: (slugs: string[]) => void;
  toggleJobType: (jt: JobType) => void;
  toggleCategory: (id: number, max: number) => boolean;
  setPendingName: (name: string) => void;
  setPendingAuth: (auth: AuthOut | null) => void;
  reset: () => void;
}

export const useOnboardingDraft = create<OnboardingDraftState>()((set, get) => ({
  suggestedCategorySlugs: [],
  selectedJobTypes: [],
  selectedCategoryIds: [],
  pendingName: "",
  pendingAuth: null,

  setSuggestedCategorySlugs: (slugs) => set({ suggestedCategorySlugs: slugs }),
  setPendingName: (name) => set({ pendingName: name }),
  setPendingAuth: (auth) => set({ pendingAuth: auth }),

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
      pendingAuth: null,
    }),
}));
