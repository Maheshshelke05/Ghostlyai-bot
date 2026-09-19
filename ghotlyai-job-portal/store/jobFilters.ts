import { create } from "zustand";

import type { JobFilters } from "@/lib/api";

interface JobFiltersState {
  filters: JobFilters;
  setFilters: (filters: JobFilters) => void;
  clear: () => void;
}

export const useJobFiltersStore = create<JobFiltersState>()((set) => ({
  filters: {},
  setFilters: (filters) => set({ filters }),
  clear: () => set({ filters: {} }),
}));

export function countActiveFilters(filters: JobFilters): number {
  return Object.values(filters).filter((v) => v !== undefined && v !== "").length;
}
