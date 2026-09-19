import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import type { JobType } from "@/lib/api";
import { useOnboardingDraft } from "@/store/onboardingDraft";

const OPTIONS: { value: JobType; label: string; icon: string }[] = [
  { value: "govt", label: "Government", icon: "🏛" },
  { value: "private", label: "Private", icon: "🏢" },
  { value: "internship", label: "Internship", icon: "🎓" },
  { value: "wfh", label: "Work from home", icon: "🏠" },
];

export default function JobTypesScreen() {
  const selected = useOnboardingDraft((s) => s.selectedJobTypes);
  const toggleJobType = useOnboardingDraft((s) => s.toggleJobType);

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={1} />
        <Text className="font-display text-ink text-[26px] mb-2">What kind of jobs?</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          Pick as many as you like. Leave all unselected to see every type.
        </Text>

        <View className="gap-3">
          {OPTIONS.map((opt) => {
            const isSelected = selected.includes(opt.value);
            return (
              <Pressable
                key={opt.value}
                onPress={() => toggleJobType(opt.value)}
                className={`flex-row items-center rounded-2xl px-4 border ${
                  isSelected ? "bg-brand-soft border-brand" : "bg-surface border-line"
                }`}
                style={{ height: 64 }}
              >
                <Text className="text-2xl mr-3">{opt.icon}</Text>
                <Text className={`flex-1 font-body-strong text-[16px] ${isSelected ? "text-brand" : "text-ink"}`}>
                  {opt.label}
                </Text>
                {isSelected ? <Text className="text-brand text-lg">✓</Text> : null}
              </Pressable>
            );
          })}
        </View>
      </View>

      <View className="mb-4">
        <Button label="Continue" onPress={() => router.push("/(onboarding)/categories")} />
      </View>
    </SafeAreaView>
  );
}
