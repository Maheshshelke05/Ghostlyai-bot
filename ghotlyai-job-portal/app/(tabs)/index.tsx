import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { MotiView } from "moti";
import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { JobCard } from "@/components/JobCard";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, browseJobs, getCategories } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { countActiveFilters, useJobFiltersStore } from "@/store/jobFilters";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function HomeScreen() {
  const [query, setQuery] = useState("");
  const filters = useJobFiltersStore((s) => s.filters);
  const setFilters = useJobFiltersStore((s) => s.setFilters);
  const activeFilterCount = countActiveFilters(filters);
  const user = useAuthStore((s) => s.user);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: () => getCategories() });
  const myCategories = useMemo(
    () => (categories ?? []).filter((c) => user?.category_ids.includes(c.id)),
    [categories, user?.category_ids]
  );

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ["jobs", filters, query],
    queryFn: ({ pageParam }) => browseJobs({ ...filters, q: query || undefined }, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  const jobs = data?.pages.flatMap((p) => p.items) ?? [];
  const firstName = user?.full_name?.split(" ")[0];

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top"]}>
      <View className="px-4 pt-2 pb-3 bg-background">
        <MotiView
          from={{ opacity: 0, translateY: -6 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ type: "timing", duration: 280 }}
        >
          <Text className="text-muted text-[13px]">{greeting()}{firstName ? `, ${firstName}` : ""} 👋</Text>
          <Text className="font-display text-ink text-[26px] mb-3">Find your next job</Text>
        </MotiView>

        <View className="flex-row items-center gap-2">
          <SearchBar value={query} onChangeText={setQuery} placeholder="Search jobs, companies..." />
          <Pressable
            onPress={() => router.push("/filters")}
            className="w-11 h-11 rounded-xl bg-surface border border-line items-center justify-center"
          >
            <Text className="text-lg">🎛️</Text>
            {activeFilterCount > 0 ? (
              <View className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-brand items-center justify-center">
                <Text className="text-white text-[10px] font-bold">{activeFilterCount}</Text>
              </View>
            ) : null}
          </Pressable>
        </View>

        {myCategories.length > 1 ? (
          <View className="flex-row flex-wrap mt-3">
            <Chip label="All" selected={!filters.category_id} onPress={() => setFilters({ ...filters, category_id: undefined })} />
            {myCategories.map((c) => (
              <Chip
                key={c.id}
                label={c.name}
                selected={filters.category_id === c.id}
                onPress={() => setFilters({ ...filters, category_id: filters.category_id === c.id ? undefined : c.id })}
              />
            ))}
          </View>
        ) : null}
      </View>

      {isError ? (
        <View className="px-4">
          <View className="items-center py-10">
            <Text className="text-muted text-center mb-4">
              {apiErrorMessage(error, "Couldn't load jobs. Check your internet connection.")}
            </Text>
            <View className="w-40">
              <Button label="Retry" onPress={() => refetch()} variant="brand" />
            </View>
          </View>
        </View>
      ) : isLoading ? (
        <ListSkeleton />
      ) : jobs.length === 0 ? (
        <EmptyState
          emoji="🔍"
          title={
            activeFilterCount > 0 || query
              ? "No jobs match your search or filters."
              : "No jobs in your categories yet. New jobs are added daily — check back soon!"
          }
        />
      ) : (
        <FlashList
          data={jobs}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item, index }) => <JobCard job={item} index={index} />}
          onEndReached={() => {
            if (hasNextPage && !isFetchingNextPage) fetchNextPage();
          }}
          onEndReachedThreshold={0.4}
          refreshing={isRefetching}
          onRefresh={refetch}
          contentContainerStyle={{ paddingTop: 4, paddingBottom: 24 }}
        />
      )}
    </SafeAreaView>
  );
}
