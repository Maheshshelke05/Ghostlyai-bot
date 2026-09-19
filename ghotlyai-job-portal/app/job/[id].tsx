import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as WebBrowser from "expo-web-browser";
import { useLocalSearchParams } from "expo-router";
import { MotiView } from "moti";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, getJob } from "@/lib/api";
import { daysUntil, formatDateDDMMYYYY } from "@/lib/dates";

const JOB_TYPE_LABEL: Record<string, string> = {
  govt: "Government",
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

export default function JobDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const jobId = Number(id);
  const queryClient = useQueryClient();

  const { data: job, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
  });

  async function onApply() {
    if (!job) return;
    await WebBrowser.openBrowserAsync(job.apply_url);
    queryClient.invalidateQueries({ queryKey: ["job", jobId] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
  }

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
        <ListSkeleton count={3} />
      </SafeAreaView>
    );
  }

  if (isError || !job) {
    return (
      <SafeAreaView className="flex-1 bg-background items-center justify-center px-6" edges={["bottom"]}>
        <Text className="text-muted text-center mb-4">
          {apiErrorMessage(error, "This job is no longer available.")}
        </Text>
        <View className="w-40">
          <Button label="Retry" onPress={() => refetch()} variant="brand" />
        </View>
      </SafeAreaView>
    );
  }

  const days = daysUntil(job.last_date);
  const urgent = days !== null && days <= 3;
  const lastDateLabel = formatDateDDMMYYYY(job.last_date);

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 120 }}>
        <MotiView
          from={{ opacity: 0, translateY: 10 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 320 }}
        >
          <View className="flex-row items-start mb-4">
            <View className="w-14 h-14 rounded-2xl bg-brand-soft items-center justify-center mr-3">
              <Text className="text-brand font-display text-xl">
                {job.company.trim().charAt(0).toUpperCase()}
              </Text>
            </View>
            <View className="flex-1">
              <Text className="font-display text-ink text-[20px]">{job.title}</Text>
              <Text className="font-body-strong text-muted text-[15px] mt-0.5">{job.company}</Text>
            </View>
          </View>

          <View className="flex-row flex-wrap gap-2 mb-5">
            <Badge label={`${JOB_TYPE_ICON[job.job_type] ?? ""} ${JOB_TYPE_LABEL[job.job_type] ?? job.job_type}`} tone="brand" />
            {job.qualification ? <Badge label={job.qualification} tone="muted" /> : null}
            {lastDateLabel ? (
              <Badge label={`Apply by ${lastDateLabel}`} tone={urgent ? "danger" : "accent"} />
            ) : null}
            {job.clicked ? <Badge label="Applied" tone="muted" /> : null}
          </View>

          {days !== null ? (
            <View className={`rounded-2xl px-4 py-3 mb-4 ${urgent ? "bg-danger/10" : "bg-brand-soft"}`}>
              <Text className={`font-body-strong text-[14px] ${urgent ? "text-danger" : "text-brand"}`}>
                {days > 0 ? `⏳ ${days} day${days === 1 ? "" : "s"} left to apply` : "⏳ Last day to apply is today"}
              </Text>
            </View>
          ) : null}

          <View className="bg-surface rounded-2xl p-4 mb-4">
            <Row label="📍 Location" value={job.location_text || job.district || "Anywhere in Maharashtra"} />
            {job.salary ? <Row label="💰 Salary" value={job.salary} /> : null}
            {job.qualification ? <Row label="🎓 Qualification" value={job.qualification} /> : null}
          </View>

          {job.description ? (
            <View className="bg-surface rounded-2xl p-4 mb-4">
              <Text className="font-body-strong text-ink text-[15px] mb-2">Job details</Text>
              <Text className="font-body text-ink text-[15px] leading-6">{job.description}</Text>
            </View>
          ) : null}

          <View className="bg-brand-soft rounded-2xl p-4">
            <Text className="text-brand text-[13px] font-body-strong">
              ✅ Verified job with an official apply link — this is a job alert service, not a
              job guarantee.
            </Text>
          </View>
        </MotiView>
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-surface border-t border-line px-5 pt-3 pb-6">
        <Button label={job.clicked ? "Apply again" : "Apply now"} onPress={onApply} />
      </View>
    </SafeAreaView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between py-1.5">
      <Text className="text-muted text-[14px]">{label}</Text>
      <Text className="text-ink text-[14px] font-body-strong flex-1 text-right ml-4">{value}</Text>
    </View>
  );
}
