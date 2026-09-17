import { router } from "expo-router";
import { Swipeable } from "react-native-gesture-handler";
import { Platform, Pressable, Text, View } from "react-native";

import { Badge } from "@/components/ui/Badge";
import type { JobOut } from "@/lib/api";

const JOB_TYPE_ICON: Record<string, string> = {
  govt: "🏛",
  private: "🏢",
  internship: "🎓",
  wfh: "🏠",
};

const cardShadow = Platform.select({
  ios: { shadowColor: "#1E2420", shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } },
  android: { elevation: 1 },
  default: {},
});

export function JobCard({ job, onDelete }: { job: JobOut; onDelete: (job: JobOut) => void }) {
  return (
    <Swipeable
      renderRightActions={() => (
        <Pressable
          onPress={() => onDelete(job)}
          className="bg-danger justify-center items-center px-6 rounded-r-[18px]"
        >
          <Text className="text-white font-semibold">Delete</Text>
        </Pressable>
      )}
      overshootRight={false}
    >
      <Pressable
        onPress={() => router.push(`/jobs/${job.id}`)}
        className="bg-surface rounded-2xl p-4 mb-2 mx-4 active:opacity-70"
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
          {job.status !== "active" ? <Badge label={job.status} tone={job.status === "expired" ? "muted" : "danger"} /> : null}
        </View>

        <View className="flex-row items-center flex-wrap gap-2 mt-2">
          {job.category_slug ? <Badge label={job.category_slug} tone="brand" /> : null}
          <Text className="text-xs text-muted">
            {JOB_TYPE_ICON[job.job_type] ?? ""} {job.location_text ?? "Anywhere"}
          </Text>
          {job.last_date ? <Text className="text-xs text-muted">⏳ {job.last_date}</Text> : null}
        </View>

        <View className="flex-row items-center gap-4 mt-2">
          <Text className="text-xs text-muted">📤 {job.sent_count}</Text>
          <Text className="text-xs text-muted">👆 {job.click_count}</Text>
        </View>
      </Pressable>
    </Swipeable>
  );
}
