import { useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, batchCreateJobs, type JobIn } from "@/lib/api";
import { useAiDraftsStore } from "@/store/aiDrafts";

function toJobIn(d: ReturnType<typeof useAiDraftsStore.getState>["drafts"][number]): JobIn {
  return {
    title: d.title ?? "",
    company: d.company ?? "",
    category_slug: d.category_slug || "other",
    qualification: d.qualification,
    district: d.district,
    location_text: d.location_text,
    job_type: d.job_type,
    salary: d.salary,
    apply_link: d.apply_link ?? "",
    last_date: d.last_date,
    description: d.description,
  };
}

export default function AiReviewScreen() {
  const drafts = useAiDraftsStore((s) => s.drafts);
  const updateDraft = useAiDraftsStore((s) => s.updateDraft);
  const removeDraft = useAiDraftsStore((s) => s.removeDraft);
  const clear = useAiDraftsStore((s) => s.clear);
  const { show } = useToast();
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);

  if (drafts.length === 0) {
    return (
      <View className="flex-1 bg-background">
        <EmptyState emoji="🤖" title="Kontihi drafts nahit. Aadhi AI paste tab varun jobs kadha." />
      </View>
    );
  }

  const saveAll = async () => {
    setSaving(true);
    try {
      const result = await batchCreateJobs(drafts.map(toJobIn));
      show(`Saved: ${result.created}, duplicates: ${result.duplicates}, errors: ${result.errors.length}`, "success");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      clear();
      router.back();
    } catch (err) {
      show(apiErrorMessage(err, "Save fail zala"), "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        {drafts.map((draft, index) => {
          const missingTitle = !draft.title;
          const missingLink = !draft.apply_link;
          return (
            <View
              key={index}
              className={`bg-surface rounded-2xl border p-4 mb-3 ${
                missingTitle || missingLink ? "border-danger" : "border-line/60"
              }`}
            >
              <View className="flex-row justify-between items-start mb-2">
                <Text className="text-xs font-semibold text-muted">Draft {index + 1}</Text>
                <Pressable onPress={() => removeDraft(index)}>
                  <Text className="text-danger text-xs font-semibold">Remove</Text>
                </Pressable>
              </View>

              <DraftField
                label="Title"
                value={draft.title ?? ""}
                error={missingTitle}
                onChange={(v) => updateDraft(index, { ...draft, title: v })}
              />
              <DraftField
                label="Company"
                value={draft.company ?? ""}
                onChange={(v) => updateDraft(index, { ...draft, company: v })}
              />
              <DraftField
                label="Category slug"
                value={draft.category_slug}
                onChange={(v) => updateDraft(index, { ...draft, category_slug: v })}
              />
              <DraftField
                label="Apply link"
                value={draft.apply_link ?? ""}
                error={missingLink}
                onChange={(v) => updateDraft(index, { ...draft, apply_link: v })}
              />
              <DraftField
                label="District"
                value={draft.district ?? ""}
                onChange={(v) => updateDraft(index, { ...draft, district: v || null })}
              />
            </View>
          );
        })}
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-background border-t border-line px-4 pt-3 pb-6">
        <Button label={`Sagle save (${drafts.length})`} onPress={saveAll} loading={saving} variant="primary" />
      </View>
    </View>
  );
}

function DraftField({
  label,
  value,
  onChange,
  error,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: boolean;
}) {
  return (
    <View className="mb-2">
      <Text className={`text-xs font-semibold mb-1 ${error ? "text-danger" : "text-muted"}`}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        className={`bg-background border rounded-xl px-3 py-2.5 text-ink text-sm ${
          error ? "border-danger" : "border-line"
        }`}
      />
    </View>
  );
}
