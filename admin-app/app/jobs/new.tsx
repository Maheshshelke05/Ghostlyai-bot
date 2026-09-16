import { useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { AiPasteTab } from "@/components/jobs/AiPasteTab";
import { ExcelUploadTab } from "@/components/jobs/ExcelUploadTab";
import { JobForm } from "@/components/jobs/JobForm";
import { createJob } from "@/lib/api";

type TabKey = "form" | "excel" | "ai";

const TABS: { key: TabKey; label: string }[] = [
  { key: "form", label: "Form" },
  { key: "excel", label: "Excel" },
  { key: "ai", label: "AI paste" },
];

export default function NewJobScreen() {
  const [tab, setTab] = useState<TabKey>("form");
  const queryClient = useQueryClient();

  return (
    <View className="flex-1 bg-background">
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
