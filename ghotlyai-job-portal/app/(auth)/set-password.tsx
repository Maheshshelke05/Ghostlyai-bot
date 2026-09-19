import { router } from "expo-router";
import { AnimatePresence, MotiView } from "moti";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage, setPassword as apiSetPassword } from "@/lib/api";
import { useOnboardingDraft } from "@/store/onboardingDraft";

export default function SetPasswordScreen() {
  const pendingSignup = useOnboardingDraft((s) => s.pendingSignup);
  const setLoginPrefill = useOnboardingDraft((s) => s.setLoginPrefill);
  const setPendingSignup = useOnboardingDraft((s) => s.setPendingSignup);

  const [password, setPasswordInput] = useState("");
  const [confirm, setConfirm] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!pendingSignup?.signup_token) {
    router.replace("/(auth)/welcome");
    return null;
  }

  const needsPhone = !pendingSignup.phone && !pendingSignup.email;
  const canSubmit =
    password.length >= 8 && password === confirm && (!needsPhone || phone.replace(/\D/g, "").length === 10);

  async function onSubmit() {
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const result = await apiSetPassword(
        pendingSignup!.signup_token!,
        password,
        needsPhone ? phone.replace(/\D/g, "") : undefined
      );
      setDone(true);
      setTimeout(() => {
        setLoginPrefill(result.phone ?? result.email ?? "");
        setPendingSignup(null);
        router.replace("/(auth)/login");
      }, 1400);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not set your password."));
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 items-center justify-center">
        <AnimatePresence>
          {done ? (
            <MotiView
              key="success"
              from={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", damping: 12 }}
              className="items-center"
            >
              <Text className="text-6xl mb-4">✅</Text>
              <Text className="font-display text-ink text-[22px]">Account created!</Text>
              <Text className="font-body text-muted text-[15px] mt-1">Taking you to login...</Text>
            </MotiView>
          ) : (
            <MotiView key="form" from={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full">
              <Text className="text-5xl mb-6 text-center">🔒</Text>
              <Text className="font-display text-ink text-[26px] text-center mb-2">Set a password</Text>
              <Text className="font-body text-muted text-[15px] text-center mb-8 px-2">
                You'll use this to log in next time — no need to upload your resume again.
              </Text>

              <TextInput
                value={password}
                onChangeText={setPasswordInput}
                placeholder="New password (min. 8 characters)"
                placeholderTextColor="#8E8E93"
                secureTextEntry
                className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink mb-3"
                style={{ height: 56 }}
              />
              <TextInput
                value={confirm}
                onChangeText={setConfirm}
                placeholder="Confirm password"
                placeholderTextColor="#8E8E93"
                secureTextEntry
                className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink mb-3"
                style={{ height: 56 }}
              />

              {needsPhone ? (
                <View
                  className="flex-row items-center bg-surface border border-line rounded-2xl px-4 mb-3"
                  style={{ height: 56 }}
                >
                  <Text className="font-body-strong text-ink text-[17px] mr-2">+91</Text>
                  <View className="w-px h-6 bg-line mr-3" />
                  <TextInput
                    value={phone}
                    onChangeText={(t) => setPhone(t.replace(/\D/g, "").slice(0, 10))}
                    placeholder="Your mobile number (resume had none)"
                    placeholderTextColor="#8E8E93"
                    keyboardType="number-pad"
                    maxLength={10}
                    className="flex-1 text-[16px] text-ink"
                  />
                </View>
              ) : null}

              {error ? <Text className="text-danger text-[13px] mb-3">{error}</Text> : null}

              <Button label="Create account" onPress={onSubmit} loading={loading} disabled={!canSubmit} />
            </MotiView>
          )}
        </AnimatePresence>
      </View>
    </SafeAreaView>
  );
}
