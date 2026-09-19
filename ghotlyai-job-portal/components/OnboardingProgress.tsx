import { Text, View } from "react-native";

const STEPS = ["Name", "District", "Resume", "Job type", "Categories"];

export function OnboardingProgress({ step }: { step: number }) {
  return (
    <View className="mb-8">
      <Text className="font-body-strong text-muted text-[13px] mb-2">
        Step {step} of {STEPS.length}
      </Text>
      <View className="flex-row gap-1.5">
        {STEPS.map((_, i) => (
          <View
            key={i}
            className={`flex-1 h-1.5 rounded-full ${i < step ? "bg-brand" : "bg-line"}`}
          />
        ))}
      </View>
    </View>
  );
}
