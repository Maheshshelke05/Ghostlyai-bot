import { useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { AiPasteTab } from "@/components/jobs/AiPasteTab";
import { ExcelUploadTab } from "@/components/jobs/ExcelUploadTab";
import { JobForm, type JobFormData } from "@/components/jobs/JobForm";
import { createJob } from "@/lib/api";

type TabKey = "form" | "excel" | "ai";

const TABS: { key: TabKey; label: string }[] = [
  { key: "form", label: "Form" },
  { key: "excel", label: "Excel" },
  { key: "ai", label: "AI paste" },
];

export default function NewJobScreen() {
  const params = useLocalSearchParams<{
    dup_title?: string;
    dup_company?: string;
    dup_category_slug?: string;
    dup_qualification?: string;
    dup_location_text?: string;
    dup_job_type?: string;
    dup_salary?: string;
  }>();
  const isDuplicate = !!params.dup_title;
  const [tab, setTab] = useState<TabKey>("form");
  const queryClient = useQueryClient();

  const duplicateDefaults: Partial<JobFormData> | undefined = isDuplicate
    ? {
        title: params.dup_title,
        company: params.dup_company,
        category_slug: params.dup_category_slug || undefined,
        qualification: params.dup_qualification,
        location_text: params.dup_location_text,
        job_type: (params.dup_job_type as JobFormData["job_type"]) || undefined,
        salary: params.dup_salary,
        apply_link: "",
        last_date: "",
      }
    : undefined;

  return (
    <View className="flex-1 bg-background">
      {isDuplicate ? (
        <View className="mx-4 mt-3 bg-brand/10 border border-brand/30 rounded-xl px-3 py-2">
          <Text className="text-xs font-semibold text-ink">
            📋 Duplicating "{params.dup_title}" — check apply link &amp; last date before saving
          </Text>
        </View>
      ) : null}
      <View className="flex-row bg-surface mx-4 mt-3 rounded-2xl p-1 border border-line/60">
        {TABS.map((t) => (
          <Pressable
            key={t.key}
            onPress={() => setTab(t.key)}
            className={`flex-1 items-center py-2.5 rounded-xl ${tab === t.key ? "bg-brand" : ""}`}
          >
            <Text className={`text-sm font-semibold ${tab === t.key ? "text-brand-ink" : "text-muted"}`}>
              {t.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {tab === "form" ? (
        <JobForm
          defaultValues={duplicateDefaults}
          submitLabel="Save"
          showSaveAndNew
          onSubmit={async (data) => {
            await createJob(data);
            queryClient.invalidateQueries({ queryKey: ["jobs"] });
            router.back();
          }}
          onSubmitAndNew={async (data) => {
            await createJob(data);
            queryClient.invalidateQueries({ queryKey: ["jobs"] });
          }}
        />
      ) : null}
      {tab === "excel" ? <ExcelUploadTab /> : null}
      {tab === "ai" ? <AiPasteTab /> : null}
    </View>
  );
}
