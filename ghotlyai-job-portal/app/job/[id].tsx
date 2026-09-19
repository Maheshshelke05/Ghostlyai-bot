import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as WebBrowser from "expo-web-browser";
import { useLocalSearchParams } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, getJob } from "@/lib/api";

const JOB_TYPE_LABEL: Record<string, string> = {
  govt: "Government",
  private: "Private",
  internship: "Internship",
  wfh: "Work from home",
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

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 120 }}>
        <Text className="font-display text-ink text-[22px] mb-1">{job.title}</Text>
        <Text className="font-body-strong text-muted text-[16px] mb-4">{job.company}</Text>

        <View className="flex-row flex-wrap gap-2 mb-5">
          <Badge label={JOB_TYPE_LABEL[job.job_type] ?? job.job_type} tone="brand" />
          {job.qualification ? <Badge label={job.qualification} tone="muted" /> : null}
          {job.last_date ? <Badge label={`Apply by ${job.last_date}`} tone="accent" /> : null}
        </View>

        <View className="bg-surface rounded-2xl p-4 mb-4">
          <Row label="📍 Location" value={job.location_text || job.district || "Anywhere in Maharashtra"} />
          {job.salary ? <Row label="💰 Salary" value={job.salary} /> : null}
        </View>

        {job.description ? (
          <View className="mb-4">
            <Text className="font-body-strong text-ink text-[15px] mb-2">Details</Text>
            <Text className="font-body text-ink text-[15px] leading-6">{job.description}</Text>
          </View>
        ) : null}
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
