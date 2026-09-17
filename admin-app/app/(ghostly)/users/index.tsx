import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage } from "@/lib/api";
import { firstOfString, isBlockedUser, type AnyRecord } from "@/lib/ghostlyFormat";
import { listGhostlyUsers } from "@/lib/ghostlyApi";

type FilterKey = "all" | "new_today";

export default function GhostlyUsersScreen() {
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{ filter?: string }>();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>(params.filter === "new_today" ? "new_today" : "all");

  useEffect(() => {
    if (params.filter === "new_today") setFilter("new_today");
  }, [params.filter]);

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ["ghostly-users", query, filter],
    queryFn: () => listGhostlyUsers({ search: query || undefined, filter: filter === "new_today" ? "new_today" : undefined }),
  });

  const users = data ?? [];

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <ScreenHeader title="Users" subtitle={`${users.length} shown`} />
      <View className="px-4">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search by name or email" />
        <View className="flex-row flex-wrap">
          <Chip label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
          <Chip label="New today" selected={filter === "new_today"} onPress={() => setFilter("new_today")} />
        </View>
      </View>

      {error ? (
        <View className="mx-4 mb-2 bg-danger/10 rounded-2xl p-3">
          <Text className="text-danger text-[13px]">{apiErrorMessage(error)}</Text>
        </View>
      ) : null}

      {isLoading ? (
        <ListSkeleton />
      ) : users.length === 0 ? (
        <EmptyState emoji="👥" title="No users found." />
      ) : (
        <ScrollView
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 40 }}
          refreshControl={<RefreshControl refreshing={isFetching} onRefresh={refetch} tintColor="#EA580C" />}
        >
          {users.map((u, i) => (
            <UserRow key={firstOfString(u, ["id", "_id", "uid", "user_id"], String(i))} user={u} />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

function UserRow({ user }: { user: AnyRecord }) {
  const id = firstOfString(user, ["id", "_id", "uid", "user_id"]);
  const name = firstOfString(user, ["name", "full_name", "username"], "Unnamed");
  const email = firstOfString(user, ["email", "email_address"]);
  const plan = firstOfString(user, ["plan", "subscription_plan", "tier"], "free");
  const blocked = isBlockedUser(user);
  const isPro = plan.toLowerCase().includes("pro");

  return (
    <Pressable
      onPress={() =>
        router.push({
          pathname: "/ghostly-user/[id]",
          params: { id: id || name, data: JSON.stringify(user) },
        })
      }
      className="bg-surface rounded-2xl px-4 py-3.5 mb-2 mx-4 flex-row items-center active:opacity-70"
    >
      <View className="w-11 h-11 rounded-full bg-brand-soft items-center justify-center mr-3">
        <Text className="text-brand font-bold text-base">{name.trim().charAt(0).toUpperCase() || "?"}</Text>
      </View>
      <View className="flex-1">
        <Text className="text-[16px] font-semibold text-ink" numberOfLines={1}>
          {name}
        </Text>
        {email ? (
          <Text className="text-[13px] text-muted mt-0.5" numberOfLines={1}>
            {email}
          </Text>
        ) : null}
      </View>
      <View className="items-end ml-2">
        <View className={`rounded-full px-2.5 py-1 ${isPro ? "bg-brand" : "bg-line"}`}>
          <Text className={`text-[11px] font-bold ${isPro ? "text-white" : "text-muted"}`}>{plan.toUpperCase()}</Text>
        </View>
        {blocked ? <Text className="text-danger text-[11px] font-semibold mt-1">Blocked</Text> : null}
      </View>
    </Pressable>
  );
}
