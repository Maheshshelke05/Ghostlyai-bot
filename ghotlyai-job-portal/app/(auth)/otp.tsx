import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Platform, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage } from "@/lib/api";
import { confirmOtp, sendOtp } from "@/lib/firebaseAuth";
import { useAuthStore } from "@/store/auth";

export default function OtpScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<TextInput>(null);
  const loginWithPhone = useAuthStore((s) => s.loginWithPhone);

  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(t);
  }, []);

  // Android auto-verifies the SMS in the background via Play Services' SMS Retriever - when
  // that happens, confirmOtp() below still runs the same way once the code lands in `code`
  // (React Native Firebase auto-fills the credential once code is set); this input just also
  // benefits from the platform's own SMS autofill suggestion in the meantime.
  async function onVerify(candidate?: string) {
    const value = candidate ?? code;
    if (value.length !== 6) return;
    setError(null);
    setLoading(true);
    try {
      const idToken = await confirmOtp(value);
      await loginWithPhone(idToken);
      // Root layout's Stack.Protected guards react to the store update and route automatically.
    } catch (err: any) {
      setError(err?.message || apiErrorMessage(err, "Could not verify the code."));
      setLoading(false);
    }
  }

  async function onResend() {
    if (!phone) return;
    setResending(true);
    setError(null);
    try {
      await sendOtp(phone);
    } catch (err: any) {
      setError(err?.message || "Could not resend the code.");
    } finally {
      setResending(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 justify-center">
        <Text className="font-display text-ink text-[28px] mb-2">Enter the code</Text>
        <Text className="font-body text-muted text-[15px] mb-8">Sent via SMS to {phone}</Text>

        <TextInput
          ref={inputRef}
          value={code}
          onChangeText={(t) => {
            const digits = t.replace(/\D/g, "").slice(0, 6);
            setCode(digits);
            if (digits.length === 6) onVerify(digits);
          }}
          placeholder="••••••"
          placeholderTextColor="#8E8E93"
          keyboardType="number-pad"
          textContentType={Platform.OS === "ios" ? "oneTimeCode" : undefined}
          autoComplete={Platform.OS === "android" ? "sms-otp" : undefined}
          maxLength={6}
          className="bg-surface border border-line rounded-2xl px-4 text-[28px] text-ink text-center tracking-[8px]"
          style={{ height: 64 }}
        />
        {error ? <Text className="text-danger text-[13px] mt-2">{error}</Text> : null}

        <View className="mt-6">
          <Button label="Resend code" onPress={onResend} loading={resending} variant="ghost" />
        </View>
      </View>

      <View className="mb-4">
        <Button label="Verify" onPress={() => onVerify()} loading={loading} disabled={code.length !== 6} />
      </View>
    </SafeAreaView>
  );
}
