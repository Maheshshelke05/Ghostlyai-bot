import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { UserRow } from "@/components/UserRow";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { listUsers, type UsersQuery } from "@/lib/api";

type FilterKey = "all" | "paid" | "trial" | "none" | "onboarding" | "blocked" | "expiring";

const FILTERS: [FilterKey, string][] = [
  ["all", "All"],
  ["paid", "Paid"],
  ["trial", "Trial"],
  ["none", "Expired"],
  ["onboarding", "Onboarding"],
  ["blocked", "Blocked"],
  ["expiring", "Expiring 3d"],
];

export default function UsersListScreen() {
  const params = useLocalSearchParams<{ expiring?: string; filter?: string }>();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>(params.expiring ? "expiring" : "all");
  const insets = useSafeAreaInsets();

  useEffect(() => {
    if (params.expiring) setFilter("expiring");
    else if (params.filter && FILTERS.some(([key]) => key === params.filter)) setFilter(params.filter as FilterKey);
  }, [params.expiring, params.filter]);

  const queryParams: UsersQuery = {
    q: query || undefined,
    page: 1,
    size: 30,
  };
  if (filter === "paid" || filter === "trial" || filter === "none") queryParams.access = filter;
  if (filter === "onboarding") queryParams.status = "onboarding";
  if (filter === "blocked") queryParams.status = "blocked";
  if (filter === "expiring") queryParams.expiring = 3;

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage, refetch, isRefetching } =
    useInfiniteQuery({
      queryKey: ["users", query, filter],
      queryFn: ({ pageParam }) => listUsers({ ...queryParams, page: pageParam }),
      initialPageParam: 1,
      getNextPageParam: (lastPage) =>
        lastPage.page * lastPage.size < lastPage.total ? lastPage.page + 1 : undefined,
    });

  const users = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <ScreenHeader
        title="Students"
        subtitle={data ? `${(data.pages[0]?.total ?? 0).toLocaleString("en-IN")} ${filter === "all" && !query ? "total" : "matching"}` : undefined}
      />
      <View className="px-4">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Name, phone or username" />
        <View className="flex-row flex-wrap">
          {FILTERS.map(([key, label]) => (
            <Chip key={key} label={label} selected={filter === key} onPress={() => setFilter(key)} />
          ))}
        </View>
      </View>

      {isLoading ? (
        <ListSkeleton />
      ) : users.length === 0 ? (
        <EmptyState emoji="👥" title="No users found." />
      ) : (
        <FlashList
          data={users}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => <UserRow user={item} />}
          onEndReached={() => {
            if (hasNextPage && !isFetchingNextPage) fetchNextPage();
          }}
          onEndReachedThreshold={0.4}
          refreshing={isRefetching}
          onRefresh={refetch}
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 40 }}
        />
      )}
    </View>
  );
}
