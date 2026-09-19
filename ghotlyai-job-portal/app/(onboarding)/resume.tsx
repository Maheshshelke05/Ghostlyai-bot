import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OnboardingProgress } from "@/components/OnboardingProgress";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiErrorMessage, type ResumeSummary, uploadResume } from "@/lib/api";
import { useOnboardingDraft } from "@/store/onboardingDraft";

export default function ResumeScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ResumeSummary | null>(null);
  const setSuggestedCategorySlugs = useOnboardingDraft((s) => s.setSuggestedCategorySlugs);

  async function submit(file: { uri: string; name: string; mimeType?: string }) {
    setError(null);
    setLoading(true);
    try {
      const result = await uploadResume(file);
      setSummary(result);
      setSuggestedCategorySlugs(result.suggested_category_slugs);
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
    <SafeAreaView className="flex-1 bg-background px-6" edges={["top", "bottom"]}>
      <View className="flex-1 pt-4">
        <OnboardingProgress step={3} />
        <Text className="font-display text-ink text-[26px] mb-2">Add your resume</Text>
        <Text className="font-body text-muted text-[15px] mb-6">
          Optional, but it helps us suggest the right job categories for you. PDF, DOCX or a
          clear photo works.
        </Text>

        {summary ? (
          <Card>
            <Text className="font-body-strong text-ink text-[15px] mb-1">
              {summary.education ?? "Education not detected"}
            </Text>
            {summary.course ? <Text className="text-muted text-[14px] mb-1">{summary.course}</Text> : null}
            {summary.skills.length > 0 ? (
              <Text className="text-muted text-[13px] mt-1">Skills: {summary.skills.join(", ")}</Text>
            ) : null}
            <Text className="text-brand text-[13px] mt-2 font-body-strong">✓ Resume added</Text>
          </Card>
        ) : (
          <View className="gap-3">
            <Button label="Choose PDF or DOCX" onPress={pickDocument} variant="ghost" loading={loading} />
            <Button label="Upload a photo instead" onPress={pickPhoto} variant="ghost" loading={loading} />
          </View>
        )}
        {error ? <Text className="text-danger text-[13px] mt-3">{error}</Text> : null}
      </View>

      <View className="mb-4 gap-3">
        <Button label={summary ? "Continue" : "Skip for now"} onPress={() => router.push("/(onboarding)/job-types")} variant={summary ? "primary" : "ghost"} />
      </View>
    </SafeAreaView>
  );
}
