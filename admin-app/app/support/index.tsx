import { FlashList } from "@shopify/flash-list";
import { useInfiniteQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, listSupportThreads, type SupportThread } from "@/lib/api";

type Filter = "open" | "all";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function SupportInboxScreen() {
  const [filter, setFilter] = useState<Filter>("open");
  const [query, setQuery] = useState("");

  const { data, isLoading, isError, error, refetch, isRefetching, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ["support", filter, query],
      queryFn: ({ pageParam }) =>
        listSupportThreads({ status: filter, q: query || undefined, page: pageParam, size: 30 }),
      initialPageParam: 1,
      getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
      refetchInterval: 30_000,
    });

  const threads = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <View className="flex-1 bg-background">
      <View className="px-4 pt-3">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search by name, phone or username" />
        <View className="flex-row">
          <Chip label="Awaiting reply" selected={filter === "open"} onPress={() => setFilter("open")} />
          <Chip label="All conversations" selected={filter === "all"} onPress={() => setFilter("all")} />
        </View>
      </View>

      {isError ? (
        <Card className="mx-4 items-center py-6">
          <Text className="text-muted text-center mb-4">
            {apiErrorMessage(error, "Couldn't load the support inbox. Check your internet connection.")}
          </Text>
          <View className="w-40">
            <Button label="Retry" onPress={() => refetch()} variant="brand" />
          </View>
        </Card>
      ) : isLoading ? (
        <ListSkeleton />
      ) : threads.length === 0 ? (
        <EmptyState
          emoji="💬"
          title={filter === "open" ? "No messages waiting for a reply." : "No support conversations yet."}
        />
      ) : (
        <FlashList
          data={threads}
          keyExtractor={(t) => String(t.user_id)}
          renderItem={({ item }) => <ThreadRow thread={item} />}
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

function ThreadRow({ thread }: { thread: SupportThread }) {
  const name = thread.full_name || thread.username || `User #${thread.user_id}`;
  return (
    <Pressable
      onPress={() => router.push(`/support/${thread.user_id}`)}
      className="bg-surface rounded-2xl px-4 py-3.5 mb-2 mx-4 flex-row items-center active:opacity-70"
    >
      <View className="w-11 h-11 rounded-full bg-brand-soft items-center justify-center mr-3">
        <Text className="text-brand font-bold text-base">{name.trim().charAt(0).toUpperCase()}</Text>
      </View>
      <View className="flex-1">
        <View className="flex-row items-center justify-between">
          <Text className="text-[16px] font-semibold text-ink" numberOfLines={1}>
            {name}
          </Text>
          <Text className="text-xs text-muted ml-2">{timeAgo(thread.last_at)}</Text>
        </View>
        <Text className="text-[14px] text-muted mt-0.5" numberOfLines={1}>
          {thread.last_direction === "out" ? "You: " : ""}
          {thread.last_message ?? ""}
        </Text>
      </View>
      {thread.awaiting_reply ? <View className="w-2.5 h-2.5 rounded-full bg-brand ml-3" /> : null}
    </Pressable>
  );
}
