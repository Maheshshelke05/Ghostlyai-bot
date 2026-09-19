import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import type { JobType } from "@/lib/api";
import { getCategories } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useJobFiltersStore } from "@/store/jobFilters";

const JOB_TYPES: { value: JobType; label: string }[] = [
  { value: "govt", label: "Government" },
  { value: "private", label: "Private" },
  { value: "internship", label: "Internship" },
  { value: "wfh", label: "Work from home" },
];

export default function FiltersScreen() {
  const filters = useJobFiltersStore((s) => s.filters);
  const setFilters = useJobFiltersStore((s) => s.setFilters);
  const clear = useJobFiltersStore((s) => s.clear);
  const myCategoryIds = useAuthStore((s) => s.user?.category_ids ?? []);

  const [categoryId, setCategoryId] = useState(filters.category_id);
  const [jobType, setJobType] = useState(filters.job_type);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: () => getCategories() });

  const myCategories = (categories ?? []).filter((c) => myCategoryIds.includes(c.id));

  function apply() {
    setFilters({
      category_id: categoryId,
      job_type: jobType,
    });
    router.back();
  }

  function reset() {
    setCategoryId(undefined);
    setJobType(undefined);
    clear();
    router.back();
  }

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
      {myCategories.length > 1 ? (
        <View className="mb-6">
          <Text className="font-body-strong text-ink text-[15px] mb-2">Category</Text>
          <View className="flex-row flex-wrap">
            <Chip label="All" selected={!categoryId} onPress={() => setCategoryId(undefined)} />
            {myCategories.map((c) => (
              <Chip key={c.id} label={c.name} selected={categoryId === c.id} onPress={() => setCategoryId(c.id)} />
            ))}
          </View>
        </View>
      ) : null}

      <View className="mb-6">
        <Text className="font-body-strong text-ink text-[15px] mb-2">Job type</Text>
        <View className="flex-row flex-wrap">
          <Chip label="All" selected={!jobType} onPress={() => setJobType(undefined)} />
          {JOB_TYPES.map((jt) => (
            <Chip key={jt.value} label={jt.label} selected={jobType === jt.value} onPress={() => setJobType(jt.value)} />
          ))}
        </View>
      </View>

      <View className="gap-3 mt-4">
        <Button label="Apply filters" onPress={apply} />
        <Button label="Clear all" onPress={reset} variant="ghost" />
      </View>
    </ScrollView>
  );
}
