import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useRef, useState } from "react";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";
import { BottomSheetModal } from "@gorhom/bottom-sheet";

import { JobForm } from "@/components/jobs/JobForm";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, deleteJob, getJob, updateJob } from "@/lib/api";

export default function JobEditScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const jobId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { show } = useToast();
  const confirmRef = useRef<BottomSheetModal>(null);

  const { data: job, isLoading } = useQuery({ queryKey: ["job", jobId], queryFn: () => getJob(jobId) });

  const deleteMutation = useMutation({
    mutationFn: () => deleteJob(jobId),
    onSuccess: () => {
      show("Job delete zala", "success");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      router.back();
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  if (isLoading || !job) {
    return (
      <View className="flex-1 bg-background items-center justify-center">
        <ActivityIndicator />
      </View>
    );
  }

  const ctr = job.sent_count > 0 ? ((job.click_count / job.sent_count) * 100).toFixed(1) : "0.0";

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        <Card className="m-4">
          <Text className="text-sm font-bold text-ink mb-2">Stats</Text>
          <View className="flex-row gap-4">
            <Stat label="Sent" value={job.sent_count} />
            <Stat label="Clicks" value={job.click_count} />
            <Stat label="CTR" value={`${ctr}%`} />
          </View>
        </Card>

        <JobForm
          defaultValues={{
            title: job.title,
            company: job.company,
            category_slug: job.category_slug ?? "",
            qualification: job.qualification ?? "",
            district: job.district ?? "",
            location_text: job.location_text ?? "",
            job_type: job.job_type,
            salary: job.salary ?? "",
            apply_link: job.apply_link,
            last_date: job.last_date ?? "",
            description: "",
          }}
          submitLabel="Update job"
          onSubmit={async (data) => {
            await updateJob(jobId, data);
            queryClient.invalidateQueries({ queryKey: ["jobs"] });
            queryClient.invalidateQueries({ queryKey: ["job", jobId] });
            show("Job update zala", "success");
            router.back();
          }}
        />

        <View className="px-4 mt-2">
          <Button label="Delete job" variant="danger" onPress={() => confirmRef.current?.present()} />
        </View>
      </ScrollView>

      <ConfirmSheet
        ref={confirmRef}
        title="Delete this job?"
        message={`"${job.title}" at ${job.company}`}
        confirmLabel="Delete"
        onConfirm={() => {
          deleteMutation.mutate();
          confirmRef.current?.dismiss();
        }}
      />
    </View>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <View className="flex-1 items-center">
      <Text className="text-lg font-extrabold text-ink">{value}</Text>
      <Text className="text-xs text-muted">{label}</Text>
    </View>
  );
}
