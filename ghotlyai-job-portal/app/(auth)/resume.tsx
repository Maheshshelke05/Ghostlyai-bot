import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { apiErrorMessage } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useOnboardingDraft } from "@/store/onboardingDraft";

export default function ResumeSignupScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signupWithResume = useAuthStore((s) => s.signupWithResume);
  const pendingName = useOnboardingDraft((s) => s.pendingName);
  const setSuggestedCategorySlugs = useOnboardingDraft((s) => s.setSuggestedCategorySlugs);
  const setPendingAuth = useOnboardingDraft((s) => s.setPendingAuth);

  async function submit(file: { uri: string; name: string; mimeType?: string }) {
    setError(null);
    setLoading(true);
    try {
      const result = await signupWithResume(file, pendingName);
      setSuggestedCategorySlugs(result.suggested_category_slugs);
      setPendingAuth(result);
      // The actual sign-in (committing to the persisted auth store, which flips the root
      // layout's Stack.Protected guards) happens at the end of the "creating your profile"
      // animation, not here - see (auth)/creating-profile.tsx.
      router.replace("/(auth)/creating-profile");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not read this file. Try a clearer PDF or photo."));
    } finally {
      setLoading(false);
    }
  }

  async function pickDocument() {
    const res = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets?.[0]) return;
    const asset = res.assets[0];
    await submit({ uri: asset.uri, name: asset.name, mimeType: asset.mimeType });
  }

  async function pickPhoto() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    if (res.canceled || !res.assets?.[0]) return;
    const asset = res.assets[0];
    await submit({ uri: asset.uri, name: "resume.jpg", mimeType: asset.mimeType ?? "image/jpeg" });
  }

  return (
    <SafeAreaView className="flex-1 bg-white px-6" edges={["top", "bottom"]}>
      <View className="flex-1 justify-center">
        <Text className="text-5xl text-center mb-6">📄</Text>
        <Text className="font-display text-ink text-[26px] text-center mb-2">Upload your resume</Text>
        <Text className="font-body text-muted text-[15px] text-center mb-10 px-4">
          We'll read your name, phone, email and education straight from it — no forms to fill,
          no OTP to wait for.
        </Text>

        <View className="gap-3">
          <Button label="Choose PDF or DOCX" onPress={pickDocument} loading={loading} />
          <Button label="Upload a photo instead" onPress={pickPhoto} loading={loading} variant="ghost" />
        </View>
        {error ? <Text className="text-danger text-[13px] text-center mt-4">{error}</Text> : null}
      </View>
    </SafeAreaView>
  );
}
