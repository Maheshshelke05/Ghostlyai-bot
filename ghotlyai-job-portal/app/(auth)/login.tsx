import { router } from "expo-router";
import { MotiView } from "moti";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useOnboardingDraft } from "@/store/onboardingDraft";

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const loginPrefill = useOnboardingDraft((s) => s.loginPrefill);

  const [identifier, setIdentifier] = useState(loginPrefill);
  const [password, setPasswordInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = identifier.trim().length >= 3 && password.length > 0;

  async function onSubmit() {
    setError(null);
    setLoading(true);
    try {
      await login(identifier.trim(), password);
      // Root layout's Stack.Protected guards react to the committed token/nextStep and swap
      // into (onboarding) or (tabs) on their own.
    } catch (err) {
      setError(apiErrorMessage(err, "Incorrect phone/email or password."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 justify-center">
        <MotiView from={{ opacity: 0, translateY: 12 }} animate={{ opacity: 1, translateY: 0 }}>
          <Text className="text-5xl mb-6 text-center">👋</Text>
          <Text className="font-display text-ink text-[26px] text-center mb-2">Welcome back</Text>
          <Text className="font-body text-muted text-[15px] text-center mb-8">
            Log in with your phone number or email and password.
          </Text>

          <TextInput
            value={identifier}
            onChangeText={setIdentifier}
            placeholder="Phone number or email"
            placeholderTextColor="#8E8E93"
            autoCapitalize="none"
            keyboardType="email-address"
            className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink mb-3"
            style={{ height: 56 }}
          />
          <TextInput
            value={password}
            onChangeText={setPasswordInput}
            placeholder="Password"
            placeholderTextColor="#8E8E93"
            secureTextEntry
            returnKeyType="done"
            onSubmitEditing={() => canSubmit && onSubmit()}
            className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink mb-3"
            style={{ height: 56 }}
          />

          {error ? <Text className="text-danger text-[13px] mb-3">{error}</Text> : null}

          <Button label="Log in" onPress={onSubmit} loading={loading} disabled={!canSubmit} />
        </MotiView>
      </View>

      <View className="mb-4 items-center">
        <Text className="font-body text-muted text-[14px]">
          New here?{" "}
          <Text className="font-body-strong text-brand" onPress={() => router.replace("/(auth)/splash")}>
            Sign up
          </Text>
        </Text>
      </View>
    </SafeAreaView>
  );
}
