import { create } from "zustand";

import type { JobDraft } from "@/lib/api";

interface AiDraftsState {
  drafts: JobDraft[];
  setDrafts: (drafts: JobDraft[]) => void;
  updateDraft: (index: number, draft: JobDraft) => void;
  removeDraft: (index: number) => void;
  clear: () => void;
}

export const useAiDraftsStore = create<AiDraftsState>((set) => ({
  drafts: [],
  setDrafts: (drafts) => set({ drafts }),
  updateDraft: (index, draft) =>
    set((state) => ({
      drafts: state.drafts.map((d, i) => (i === index ? draft : d)),
    })),
  removeDraft: (index) =>
    set((state) => ({ drafts: state.drafts.filter((_, i) => i !== index) })),
  clear: () => set({ drafts: [] }),
}));
