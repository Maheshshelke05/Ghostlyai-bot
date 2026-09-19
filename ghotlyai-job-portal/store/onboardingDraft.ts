import { create } from "zustand";

import type { JobType } from "@/lib/api";

/** In-memory only (not persisted) - holds the resume -> job-types -> categories sub-flow's
 * picks until they're all submitted together via POST /student/me/complete, mirroring how the
 * Telegram bot's FSM only commits categories+job_types at the very end of onboarding. */
interface OnboardingDraftState {
  suggestedCategorySlugs: string[];
  selectedJobTypes: JobType[];
  selectedCategoryIds: number[];
  setSuggestedCategorySlugs: (slugs: string[]) => void;
  toggleJobType: (jt: JobType) => void;
  toggleCategory: (id: number, max: number) => boolean;
  reset: () => void;
}

export const useOnboardingDraft = create<OnboardingDraftState>()((set, get) => ({
  suggestedCategorySlugs: [],
  selectedJobTypes: [],
  selectedCategoryIds: [],

  setSuggestedCategorySlugs: (slugs) => set({ suggestedCategorySlugs: slugs }),

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

  reset: () => set({ suggestedCategorySlugs: [], selectedJobTypes: [], selectedCategoryIds: [] }),
}));
