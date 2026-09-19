import { router } from "expo-router";
import { MotiView } from "moti";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { useOnboardingDraft } from "@/store/onboardingDraft";

function looksLikeFullName(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.length >= 3 && trimmed.split(/\s+/).length >= 2;
}

export default function NameScreen() {
  const [name, setName] = useState("");
  const setPendingName = useOnboardingDraft((s) => s.setPendingName);
  const canContinue = looksLikeFullName(name);

  function onNext() {
    setPendingName(name.trim());
    router.push("/(auth)/resume");
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-8">
        <MotiView
          from={{ opacity: 0, translateY: 12 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 350 }}
        >
          <Text className="text-5xl mb-6">👋</Text>
          <Text className="font-display text-ink text-[26px] mb-2">What's your name?</Text>
          <Text className="font-body text-muted text-[15px] mb-8">
            This is how we'll greet you and how your profile will show up.
          </Text>
        </MotiView>

        <MotiView
          from={{ opacity: 0, translateY: 12 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 350, delay: 120 }}
        >
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder="e.g. Rahul Sharma"
            placeholderTextColor="#8E8E93"
            autoCapitalize="words"
            autoFocus
            returnKeyType="done"
            onSubmitEditing={() => canContinue && onNext()}
            className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink"
            style={{ height: 56 }}
          />
        </MotiView>
      </View>

      <View className="mb-4">
        <Button label="Continue" onPress={onNext} disabled={!canContinue} />
      </View>
    </SafeAreaView>
  );
}
