import { router } from "expo-router";
import { useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import { apiErrorMessage, setName, setPhone } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function NameScreen() {
  const user = useAuthStore((s) => s.user);
  const [name, setNameInput] = useState(user?.full_name ?? "");
  const [phone, setPhoneInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const applyMe = useAuthStore((s) => s.applyMe);

  const needsPhone = !user?.phone;
  const canContinue = name.trim().length >= 3 && (!needsPhone || phone.replace(/\D/g, "").length === 10);

  async function onNext() {
    setError(null);
    setLoading(true);
    try {
      let me = await setName(name.trim());
      if (needsPhone) {
        me = await setPhone(phone.replace(/\D/g, ""));
      }
      applyMe(me);
      router.push("/(onboarding)/district");
    } catch (err) {
      setError(apiErrorMessage(err, "Please check your details and try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={1} />
        <Text className="font-display text-ink text-[26px] mb-2">Confirm your details</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          {user?.full_name
            ? "We picked this up from your resume — edit it if we got anything wrong."
            : "We couldn't find a name in your resume — please enter it."}
        </Text>

        <Text className="font-body-strong text-ink text-[13px] mb-1.5">Full name</Text>
        <TextInput
          value={name}
          onChangeText={setNameInput}
          placeholder="e.g. Rahul Sharma"
          placeholderTextColor="#8E8E93"
          autoCapitalize="words"
          autoFocus={!user?.full_name}
          className="bg-surface border border-line rounded-2xl px-4 text-[17px] text-ink mb-4"
          style={{ height: 56 }}
        />

        {needsPhone ? (
          <>
            <Text className="font-body-strong text-ink text-[13px] mb-1.5">
              Mobile number (not found in your resume)
            </Text>
            <View className="flex-row items-center bg-surface border border-line rounded-2xl px-4" style={{ height: 56 }}>
              <Text className="font-body-strong text-ink text-[17px] mr-2">+91</Text>
              <View className="w-px h-6 bg-line mr-3" />
              <TextInput
                value={phone}
                onChangeText={(t) => setPhoneInput(t.replace(/\D/g, "").slice(0, 10))}
                placeholder="98765 43210"
                placeholderTextColor="#8E8E93"
                keyboardType="number-pad"
                maxLength={10}
                className="flex-1 text-[17px] text-ink"
              />
            </View>
          </>
        ) : null}

        {error ? <Text className="text-danger text-[13px] mt-3">{error}</Text> : null}
      </View>

      <View className="mb-4">
        <Button label="Continue" onPress={onNext} loading={loading} disabled={!canContinue} />
      </View>
    </SafeAreaView>
  );
}
