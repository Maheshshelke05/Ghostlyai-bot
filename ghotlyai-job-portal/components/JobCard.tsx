import { router } from "expo-router";
import { MotiView } from "moti";
import { useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";

import { Badge } from "@/components/ui/Badge";
import type { JobOut } from "@/lib/api";
import { daysUntil } from "@/lib/dates";

const JOB_TYPE_LABEL: Record<string, string> = {
  govt: "Govt",
  private: "Private",
  internship: "Internship",
  wfh: "Work from home",
};
const JOB_TYPE_ICON: Record<string, string> = {
  govt: "🏛",
  private: "🏢",
  internship: "🎓",
  wfh: "🏠",
};

const cardShadow = Platform.select({
  ios: { shadowColor: "#000000", shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } },
  android: { elevation: 1 },
  default: {},
});

export function JobCard({ job, index = 0 }: { job: JobOut; index?: number }) {
  const days = daysUntil(job.last_date);
  const urgent = days !== null && days <= 3;
  const [pressed, setPressed] = useState(false);

  return (
    <MotiView
      from={{ opacity: 0, translateY: 14 }}
      animate={{ opacity: 1, translateY: 0 }}
      transition={{ type: "timing", duration: 260, delay: Math.min(index, 8) * 35 }}
    >
    <MotiView
      animate={{ scale: pressed ? 0.97 : 1 }}
      transition={{ type: "spring", damping: 18, stiffness: 320 }}
    >
    <Pressable
      onPress={() => router.push(`/job/${job.id}`)}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      className="bg-surface rounded-2xl p-4 mb-3 mx-4"
      style={cardShadow}
    >
      <View className="flex-row items-start justify-between">
        <View className="flex-1 pr-2">
          <Text className="text-base font-bold text-ink" numberOfLines={1}>
            {job.title}
          </Text>
          <Text className="text-sm text-muted mt-0.5" numberOfLines={1}>
            {job.company}
          </Text>
        </View>
        {job.clicked ? <Badge label="Applied" tone="brand" /> : null}
      </View>

      <View className="flex-row items-center flex-wrap gap-2 mt-2.5">
        <Badge
          label={`${JOB_TYPE_ICON[job.job_type] ?? ""} ${JOB_TYPE_LABEL[job.job_type] ?? job.job_type}`}
          tone="muted"
        />
        <Text className="text-xs text-muted" numberOfLines={1}>
          📍 {job.location_text || job.district || "Anywhere in Maharashtra"}
        </Text>
      </View>

      {job.salary || days !== null ? (
        <View className="flex-row items-center justify-between mt-3">
          <Text className="text-sm font-semibold text-ink">{job.salary ?? ""}</Text>
          {days !== null ? (
            <Text className={`text-xs font-semibold ${urgent ? "text-danger" : "text-muted"}`}>
              {days > 0 ? `${days} day${days === 1 ? "" : "s"} left` : "Last day today"}
            </Text>
          ) : null}
        </View>
      ) : null}
    </Pressable>
    </MotiView>
    </MotiView>
  );
}
