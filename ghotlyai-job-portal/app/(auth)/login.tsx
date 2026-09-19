import { router } from "expo-router";
import { useState } from "react";
import { Platform, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { getPhoneNumberHint, sendOtp } from "@/lib/firebaseAuth";

export default function LoginScreen() {
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function tryAutoFillFromDevice() {
    // Android-only Phone Number Hint - currently a no-op stub, see lib/firebaseAuth.ts. Safe
    // to call unconditionally: it resolves to null on iOS and until a real hint is wired up.
    const hint = await getPhoneNumberHint();
    if (hint) setPhone(hint.replace("+91", ""));
  }

  async function onContinue() {
    const digits = phone.replace(/\D/g, "");
    if (digits.length !== 10) {
      setError("Enter a valid 10-digit mobile number");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const e164 = `+91${digits}`;
      await sendOtp(e164);
      router.push({ pathname: "/(auth)/otp", params: { phone: e164 } });
    } catch (err: any) {
      setError(err?.message || "Could not send the code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 justify-center">
        <Text className="font-display text-ink text-[28px] mb-2">Your number</Text>
        <Text className="font-body text-muted text-[15px] mb-8">
          We'll text you a one-time code to confirm it's you.
        </Text>

        <View className="flex-row items-center bg-surface border border-line rounded-2xl px-4 mb-2" style={{ height: 56 }}>
          <Text className="font-body-strong text-ink text-[17px] mr-2">🇮🇳 +91</Text>
          <View className="w-px h-6 bg-line mr-3" />
          <TextInput
            value={phone}
            onChangeText={(t) => setPhone(t.replace(/\D/g, "").slice(0, 10))}
            placeholder="98765 43210"
            placeholderTextColor="#8E8E93"
            keyboardType="number-pad"
            textContentType={Platform.OS === "ios" ? "telephoneNumber" : undefined}
            maxLength={10}
            className="flex-1 text-[17px] text-ink"
            autoFocus
            onFocus={tryAutoFillFromDevice}
          />
        </View>
        {error ? <Text className="text-danger text-[13px] mb-2">{error}</Text> : null}
      </View>

      <View className="mb-4">
        <Button label="Send OTP" onPress={onContinue} loading={loading} disabled={phone.length !== 10} />
      </View>
    </SafeAreaView>
  );
}
