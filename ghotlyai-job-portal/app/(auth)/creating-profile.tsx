import { router } from "expo-router";
import { MotiView } from "moti";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useOnboardingDraft } from "@/store/onboardingDraft";

const STEPS = [
  "Reading your resume",
  "Extracting your skills and education",
  "Finding job categories that match you",
  "Setting up your profile",
];

const STEP_INTERVAL_MS = 1300;

export default function CreatingProfileScreen() {
  const pendingSignup = useOnboardingDraft((s) => s.pendingSignup);
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    if (visibleSteps >= STEPS.length) {
      const timer = setTimeout(() => router.replace("/(auth)/set-password"), 500);
      return () => clearTimeout(timer);
    }
    const timer = setTimeout(() => setVisibleSteps((n) => n + 1), STEP_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [visibleSteps]);

  if (!pendingSignup) {
    router.replace("/(auth)/welcome");
    return null;
  }

  const checklistDone = visibleSteps >= STEPS.length;

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 items-center justify-center">
        <MotiView
          from={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", damping: 10 }}
          className="items-center mb-8"
        >
          <Text className="text-6xl">✨</Text>
        </MotiView>
        <Text className="font-display text-ink text-[22px] text-center mb-8">
          Creating your profile{pendingSignup.full_name ? `, ${pendingSignup.full_name.split(" ")[0]}` : ""}...
        </Text>

        <View className="gap-4 w-full">
          {STEPS.map((step, i) => {
            const shown = i < visibleSteps;
            const active = i === visibleSteps - 1 && !checklistDone;
            if (!shown) return null;
            return (
              <MotiView
                key={step}
                from={{ opacity: 0, translateX: -12 }}
                animate={{ opacity: 1, translateX: 0 }}
                transition={{ type: "timing", duration: 300 }}
                className="flex-row items-center"
              >
                <View
                  className={`w-6 h-6 rounded-full items-center justify-center mr-3 ${
                    active ? "bg-brand-soft" : "bg-brand"
                  }`}
                >
                  <Text className={active ? "text-brand text-xs" : "text-white text-xs"}>
                    {active ? "…" : "✓"}
                  </Text>
                </View>
                <Text className="font-body text-ink text-[15px]">{step}</Text>
              </MotiView>
            );
          })}
        </View>
      </View>
    </SafeAreaView>
  );
}
