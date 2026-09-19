import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import { apiErrorMessage, completeOnboarding, getCategories, getPublicSettings } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useOnboardingDraft } from "@/store/onboardingDraft";

export default function CategoriesScreen() {
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestedSlugs = useOnboardingDraft((s) => s.suggestedCategorySlugs);
  const selectedJobTypes = useOnboardingDraft((s) => s.selectedJobTypes);
  const selectedIds = useOnboardingDraft((s) => s.selectedCategoryIds);
  const toggleCategory = useOnboardingDraft((s) => s.toggleCategory);
  const resetDraft = useOnboardingDraft((s) => s.reset);
  const applyMe = useAuthStore((s) => s.applyMe);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: () => getCategories() });
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: getPublicSettings });
  const maxCategories = settings?.max_categories ?? 3;

  const shown = useMemo(() => {
    if (!categories) return [];
    if (showAll || suggestedSlugs.length === 0) return categories;
    const suggested = categories.filter((c) => suggestedSlugs.includes(c.slug));
    const extra = categories.filter((c) => selectedIds.includes(c.id) && !suggested.includes(c));
    return [...suggested, ...extra];
  }, [categories, showAll, suggestedSlugs, selectedIds]);

  function onToggle(id: number) {
    const ok = toggleCategory(id, maxCategories);
    if (!ok) setError(`You can pick up to ${maxCategories} categories.`);
    else setError(null);
  }

  async function onFinish() {
    if (selectedIds.length === 0) {
      setError("Pick at least 1 category to continue.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const me = await completeOnboarding(selectedIds, selectedJobTypes);
      resetDraft();
      applyMe(me);
      // No explicit navigation: nextStep flips to "done" above, and the root layout's
      // Stack.Protected guards react to that and swap straight into (tabs) on their own.
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save your categories."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={2} />
        <Text className="font-display text-ink text-[26px] mb-2">Pick your job categories</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          Choose up to {maxCategories}. We'll only alert you for these.
        </Text>

        <View className="flex-row flex-wrap gap-2">
          {shown.map((cat) => {
            const isSelected = selectedIds.includes(cat.id);
            return (
              <Pressable
                key={cat.id}
                onPress={() => onToggle(cat.id)}
                className={`rounded-2xl px-4 py-3 border ${
                  isSelected ? "bg-brand-soft border-brand" : "bg-surface border-line"
                }`}
              >
                <Text className={`font-body-strong text-[14px] ${isSelected ? "text-brand" : "text-ink"}`}>
                  {isSelected ? "✓ " : ""}
                  {cat.name}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {!showAll && suggestedSlugs.length > 0 ? (
          <Pressable onPress={() => setShowAll(true)} className="mt-4">
            <Text className="font-body-strong text-brand text-[15px]">Show all categories →</Text>
          </Pressable>
        ) : null}

        {error ? <Text className="text-danger text-[13px] mt-4">{error}</Text> : null}
      </View>

      <View className="mb-4">
        <Button label="Finish" onPress={onFinish} loading={loading} disabled={selectedIds.length === 0} />
      </View>
    </SafeAreaView>
  );
}
