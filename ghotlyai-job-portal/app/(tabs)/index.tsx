import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { JobCard } from "@/components/JobCard";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, browseJobs } from "@/lib/api";
import { countActiveFilters, useJobFiltersStore } from "@/store/jobFilters";

export default function HomeScreen() {
  const [query, setQuery] = useState("");
  const filters = useJobFiltersStore((s) => s.filters);
  const activeFilterCount = countActiveFilters(filters);

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

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top"]}>
      <View className="px-4 pt-2 pb-3 bg-background">
        <Text className="font-display text-ink text-[24px] mb-3">JobKatta</Text>
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
