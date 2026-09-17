import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { JobCard } from "@/components/JobCard";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, deleteJob, listJobs, type JobOut } from "@/lib/api";

type FilterKey = "all" | "today" | "active" | "expired";

export default function JobsListScreen() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [jobToDelete, setJobToDelete] = useState<JobOut | null>(null);
  const confirmRef = useRef<BottomSheetModal>(null);
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { show } = useToast();

  const { data, isLoading, isFetchingNextPage, fetchNextPage, hasNextPage, refetch, isRefetching } =
    useInfiniteQuery({
      queryKey: ["jobs", query, filter],
      queryFn: ({ pageParam }) =>
        listJobs({
          q: query || undefined,
          status: filter === "active" || filter === "expired" ? filter : undefined,
          date: filter === "today" ? "today" : undefined,
          page: pageParam,
          size: 30,
        }),
      initialPageParam: 1,
      getNextPageParam: (lastPage) =>
        lastPage.page * lastPage.size < lastPage.total ? lastPage.page + 1 : undefined,
    });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteJob(id),
    onSuccess: () => {
      show("Job deleted", "success");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const jobs = data?.pages.flatMap((p) => p.items) ?? [];

  const onDeleteRequest = (job: JobOut) => {
    setJobToDelete(job);
    confirmRef.current?.present();
  };

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top + 8 }}>
      <View className="px-4">
        <Text className="text-2xl font-extrabold text-ink mb-3">Jobs</Text>
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search title / company" />
        <View className="flex-row flex-wrap">
          <Chip label="Today" selected={filter === "today"} onPress={() => setFilter(filter === "today" ? "all" : "today")} />
          <Chip label="Active" selected={filter === "active"} onPress={() => setFilter(filter === "active" ? "all" : "active")} />
          <Chip label="Expired" selected={filter === "expired"} onPress={() => setFilter(filter === "expired" ? "all" : "expired")} />
        </View>
      </View>

      {isLoading ? (
        <View className="px-0 mt-2">
          <ListSkeleton />
        </View>
      ) : jobs.length === 0 ? (
        <EmptyState
          emoji="💼"
          title="No jobs yet. Add your first job."
          actionLabel="Add job"
          onAction={() => router.push("/jobs/new")}
        />
      ) : (
        <FlashList
          data={jobs}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => <JobCard job={item} onDelete={onDeleteRequest} />}
          onEndReached={() => {
            if (hasNextPage && !isFetchingNextPage) fetchNextPage();
          }}
          onEndReachedThreshold={0.4}
          refreshing={isRefetching}
          onRefresh={refetch}
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 120 }}
        />
      )}

      <Pressable
        onPress={() => router.push("/jobs/new")}
        className="absolute right-5 bg-brand rounded-full items-center justify-center shadow-lg"
        style={{ bottom: insets.bottom + 20, width: 58, height: 58 }}
      >
        <Text className="text-2xl text-brand-ink">+</Text>
      </Pressable>

      <ConfirmSheet
        ref={confirmRef}
        title="Delete this job?"
        message={jobToDelete ? `"${jobToDelete.title}" at ${jobToDelete.company}` : undefined}
        confirmLabel="Delete"
        onConfirm={() => {
          if (jobToDelete) deleteMutation.mutate(jobToDelete.id);
          confirmRef.current?.dismiss();
        }}
      />
    </View>
  );
}
