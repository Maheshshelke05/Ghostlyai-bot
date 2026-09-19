import { router } from "expo-router";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import { apiErrorMessage, setName } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function NameScreen() {
  const [name, setNameInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const applyMe = useAuthStore((s) => s.applyMe);

  async function onNext() {
    setError(null);
    setLoading(true);
    try {
      const me = await setName(name.trim());
      applyMe(me);
      router.push("/(onboarding)/district");
    } catch (err) {
      setError(apiErrorMessage(err, "Please enter your full name (first and last name)."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={1} />
        <Text className="font-display text-ink text-[26px] mb-2">What's your full name?</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          This is how employers will see you referred to.
        </Text>

        <TextInput
          value={name}
          onChangeText={setNameInput}
          placeholder="e.g. Rahul Sharma"
          placeholderTextColor="#8E8E93"
          autoCapitalize="words"
          autoFocus
          className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink"
          style={{ height: 56 }}
        />
        {error ? <Text className="text-danger text-[13px] mt-2">{error}</Text> : null}
      </View>

      <View className="mb-4">
        <Button label="Continue" onPress={onNext} loading={loading} disabled={name.trim().length < 3} />
      </View>
    </SafeAreaView>
  );
}
