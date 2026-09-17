import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { JobCard } from "@/components/JobCard";
import { Chip } from "@/components/ui/Chip";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectSheet } from "@/components/ui/SelectSheet";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, deleteJob, listCategories, listJobs, type JobOut } from "@/lib/api";

type StatusFilter = "all" | "today" | "active" | "expired";
type JobType = "govt" | "private" | "internship" | "wfh";

const JOB_TYPES: { value: JobType; label: string }[] = [
  { value: "govt", label: "🏛 Govt" },
  { value: "private", label: "🏢 Private" },
  { value: "internship", label: "🎓 Internship" },
  { value: "wfh", label: "🏠 WFH" },
];

export default function JobsListScreen() {
  const params = useLocalSearchParams<{ category_id?: string; filter?: string }>();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<StatusFilter>(
    params.filter === "today" || params.filter === "active" || params.filter === "expired" ? params.filter : "all"
  );
  const [jobType, setJobType] = useState<JobType | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(params.category_id ? Number(params.category_id) : null);
  const [jobToDelete, setJobToDelete] = useState<JobOut | null>(null);
  const confirmRef = useRef<BottomSheetModal>(null);
  const categorySheetRef = useRef<BottomSheetModal>(null);
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { show } = useToast();

  useEffect(() => {
    if (params.category_id) setCategoryId(Number(params.category_id));
  }, [params.category_id]);
  useEffect(() => {
    if (params.filter === "today" || params.filter === "active" || params.filter === "expired") setFilter(params.filter);
  }, [params.filter]);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const categoryName = categories?.find((c) => c.id === categoryId)?.name;

  const { data, isLoading, isFetchingNextPage, fetchNextPage, hasNextPage, refetch, isRefetching } =
    useInfiniteQuery({
      queryKey: ["jobs", query, filter, jobType, categoryId],
      queryFn: ({ pageParam }) =>
        listJobs({
          q: query || undefined,
          status: filter === "active" || filter === "expired" ? filter : undefined,
          date: filter === "today" ? "today" : undefined,
          job_type: jobType ?? undefined,
          category_id: categoryId ?? undefined,
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
  const total = data?.pages[0]?.total ?? 0;
  const filtersActive = filter !== "all" || jobType !== null || categoryId !== null || query !== "";

  const onDeleteRequest = (job: JobOut) => {
    setJobToDelete(job);
    confirmRef.current?.present();
  };

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <ScreenHeader title="Jobs" subtitle={isLoading ? undefined : `${total.toLocaleString("en-IN")} ${filtersActive ? "matching" : "total"}`} />
      <View className="px-4">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search title or company" />
        <View className="flex-row flex-wrap">
          <Chip label="Today" selected={filter === "today"} onPress={() => setFilter(filter === "today" ? "all" : "today")} />
          <Chip label="Active" selected={filter === "active"} onPress={() => setFilter(filter === "active" ? "all" : "active")} />
          <Chip label="Expired" selected={filter === "expired"} onPress={() => setFilter(filter === "expired" ? "all" : "expired")} />
          <Chip
            label={categoryName ? `📂 ${categoryName}` : "📂 Category"}
            selected={categoryId !== null}
            onPress={() => (categoryId !== null ? setCategoryId(null) : categorySheetRef.current?.present())}
          />
        </View>
        <View className="flex-row flex-wrap">
          {JOB_TYPES.map((jt) => (
            <Chip
              key={jt.value}
              label={jt.label}
              selected={jobType === jt.value}
              onPress={() => setJobType(jobType === jt.value ? null : jt.value)}
            />
          ))}
        </View>
      </View>

      {isLoading ? (
        <View className="px-0 mt-2">
          <ListSkeleton />
        </View>
      ) : jobs.length === 0 ? (
        <EmptyState
          emoji="💼"
          title={filtersActive ? "No jobs match these filters." : "No jobs yet. Add your first job."}
          actionLabel={filtersActive ? undefined : "Add job"}
          onAction={filtersActive ? undefined : () => router.push("/jobs/new")}
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
        className="absolute right-5 bg-brand rounded-full items-center justify-center"
        style={{
          bottom: insets.bottom + 20,
          width: 58,
          height: 58,
          shadowColor: "#EA580C",
          shadowOpacity: 0.35,
          shadowRadius: 12,
          shadowOffset: { width: 0, height: 6 },
          elevation: 6,
        }}
      >
        <Text className="text-3xl text-white" style={{ marginTop: -2 }}>+</Text>
      </Pressable>

      <SelectSheet
        ref={categorySheetRef}
        title="Filter by category"
        options={(categories ?? []).map((c) => ({ label: c.name, value: String(c.id) }))}
        onSelect={(value) => {
          setCategoryId(Number(value));
          categorySheetRef.current?.dismiss();
        }}
      />

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
