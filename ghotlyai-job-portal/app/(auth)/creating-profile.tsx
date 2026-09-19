import { router } from "expo-router";
import { AnimatePresence, MotiView } from "moti";
import { useEffect, useRef, useState } from "react";
import { Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage, setPhone as apiSetPhone } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useOnboardingDraft } from "@/store/onboardingDraft";

const STEPS = [
  "Reading your resume",
  "Extracting your skills and education",
  "Finding job categories that match you",
  "Setting up your profile",
];

const STEP_INTERVAL_MS = 1400;

export default function CreatingProfileScreen() {
  const pendingAuth = useOnboardingDraft((s) => s.pendingAuth);
  const setPendingAuth = useOnboardingDraft((s) => s.setPendingAuth);
  const commitAuth = useAuthStore((s) => s.commitAuth);

  const [visibleSteps, setVisibleSteps] = useState(0);
  const [phone, setPhoneInput] = useState("");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [submittingPhone, setSubmittingPhone] = useState(false);
  const finishedRef = useRef(false);

  useEffect(() => {
    if (visibleSteps >= STEPS.length) return;
    const timer = setTimeout(() => setVisibleSteps((n) => n + 1), STEP_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [visibleSteps]);

  const checklistDone = visibleSteps >= STEPS.length;
  const needsPhone = checklistDone && !pendingAuth?.user.phone;
  const readyToFinish = checklistDone && !needsPhone;

  useEffect(() => {
    if (!readyToFinish || !pendingAuth || finishedRef.current) return;
    finishedRef.current = true;
    const timer = setTimeout(() => finish(pendingAuth.user, pendingAuth.next_step), 500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyToFinish]);

  function finish(user: NonNullable<typeof pendingAuth>["user"], nextStep: NonNullable<typeof pendingAuth>["next_step"]) {
    if (!pendingAuth) return;
    commitAuth(pendingAuth.access_token, { user, next_step: nextStep });
    setPendingAuth(null);
    // Root layout's Stack.Protected guards react to the committed token/nextStep and swap into
    // (onboarding) or (tabs) on their own.
  }

  async function onSubmitPhone() {
    const digits = phone.replace(/\D/g, "");
    if (digits.length !== 10) {
      setPhoneError("Enter a valid 10-digit mobile number.");
      return;
    }
    setPhoneError(null);
    setSubmittingPhone(true);
    try {
      const me = await apiSetPhone(digits);
      finish(me.user, me.next_step);
    } catch (err) {
      setPhoneError(apiErrorMessage(err, "Could not save this number."));
    } finally {
      setSubmittingPhone(false);
    }
  }

  if (!pendingAuth) {
    // Nothing staged (e.g. app was killed mid-flow) - nowhere useful to render, send back.
    router.replace("/(auth)/welcome");
    return null;
  }

  return (
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 items-center justify-center">
        <AnimatePresence>
          {!needsPhone ? (
            <MotiView
              key="checklist"
              from={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: "timing", duration: 250 }}
              className="w-full"
            >
              <MotiView
                from={{ scale: 0.7, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", damping: 10 }}
                className="items-center mb-8"
              >
                <Text className="text-6xl">✨</Text>
              </MotiView>
              <Text className="font-display text-ink text-[22px] text-center mb-8">
                Creating your profile{pendingAuth.user.full_name ? `, ${pendingAuth.user.full_name.split(" ")[0]}` : ""}...
              </Text>

              <View className="gap-4">
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
            </MotiView>
          ) : (
            <MotiView
              key="phone"
              from={{ opacity: 0, translateY: 16 }}
              animate={{ opacity: 1, translateY: 0 }}
              transition={{ type: "timing", duration: 300 }}
              className="w-full"
            >
              <Text className="text-5xl text-center mb-6">📱</Text>
              <Text className="font-display text-ink text-[22px] text-center mb-2">One more thing</Text>
              <Text className="font-body text-muted text-[15px] text-center mb-6">
                We couldn't find a mobile number in your resume - what's the best number to reach you?
              </Text>
              <View
                className="flex-row items-center bg-surface border border-line rounded-2xl px-4 mb-3"
                style={{ height: 56 }}
              >
                <Text className="font-body-strong text-ink text-[17px] mr-2">+91</Text>
                <View className="w-px h-6 bg-line mr-3" />
                <TextInput
                  value={phone}
                  onChangeText={(t) => setPhoneInput(t.replace(/\D/g, "").slice(0, 10))}
                  placeholder="98765 43210"
                  placeholderTextColor="#8E8E93"
                  keyboardType="number-pad"
                  maxLength={10}
                  autoFocus
                  className="flex-1 text-[17px] text-ink"
                />
              </View>
              {phoneError ? <Text className="text-danger text-[13px] mb-3">{phoneError}</Text> : null}
              <Button
                label="Continue"
                onPress={onSubmitPhone}
                loading={submittingPhone}
                disabled={phone.length !== 10}
              />
            </MotiView>
          )}
        </AnimatePresence>
      </View>
    </SafeAreaView>
  );
}
