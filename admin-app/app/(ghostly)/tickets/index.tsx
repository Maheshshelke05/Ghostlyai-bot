import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Chip } from "@/components/ui/Chip";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { SearchBar } from "@/components/ui/SearchBar";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage } from "@/lib/api";
import { firstOfString, formatValue, type AnyRecord } from "@/lib/ghostlyFormat";
import { listGhostlySupport } from "@/lib/ghostlyApi";

type Filter = "open" | "resolved" | "all";

function statusOf(t: AnyRecord): string {
  return firstOfString(t, ["status", "ticket_status", "state"], "open").toLowerCase();
}

function isResolved(status: string): boolean {
  return status === "resolved" || status === "closed";
}

export default function GhostlyTicketsScreen() {
  const insets = useSafeAreaInsets();
  const [filter, setFilter] = useState<Filter>("open");
  const [query, setQuery] = useState("");

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ["ghostly-support"],
    queryFn: listGhostlySupport,
    refetchInterval: 30_000,
  });

  const all = data ?? [];
  const openCount = all.filter((t) => !isResolved(statusOf(t))).length;
  const resolvedCount = all.length - openCount;

  const tickets = useMemo(() => {
    let list = all;
    if (filter === "open") list = list.filter((t) => !isResolved(statusOf(t)));
    if (filter === "resolved") list = list.filter((t) => isResolved(statusOf(t)));
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter((t) => JSON.stringify(t).toLowerCase().includes(q));
    }
    return list;
  }, [all, filter, query]);

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <ScreenHeader title="Support" subtitle={`${openCount} open · ${resolvedCount} resolved`} />
      <View className="px-4">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search subject, email, message…" />
        <View className="flex-row flex-wrap">
          <Chip label={`Open (${openCount})`} selected={filter === "open"} onPress={() => setFilter("open")} />
          <Chip label={`Resolved (${resolvedCount})`} selected={filter === "resolved"} onPress={() => setFilter("resolved")} />
          <Chip label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
        </View>
      </View>

      {error ? (
        <View className="mx-4 mb-2 bg-danger/10 rounded-2xl p-3">
          <Text className="text-danger text-[13px]">{apiErrorMessage(error)}</Text>
        </View>
      ) : null}

      {isLoading ? (
        <ListSkeleton />
      ) : tickets.length === 0 ? (
        <EmptyState emoji="💬" title="No support tickets here." />
      ) : (
        <ScrollView
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 40 }}
          refreshControl={<RefreshControl refreshing={isFetching} onRefresh={refetch} tintColor="#EA580C" />}
        >
          {tickets.map((t, i) => (
            <TicketRow key={firstOfString(t, ["id", "_id", "ticket_id"], String(i))} ticket={t} />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

function TicketRow({ ticket }: { ticket: AnyRecord }) {
  const id = firstOfString(ticket, ["id", "_id", "ticket_id"]);
  const subject = firstOfString(ticket, ["subject", "title"], "Support request");
  const email = firstOfString(ticket, ["email", "user_email"]);
  const message = firstOfString(ticket, ["message", "description", "body"]);
  const status = statusOf(ticket);
  const resolved = isResolved(status);
  const dateRaw = firstOfString(ticket, ["created_at", "date", "timestamp"]);

  return (
    <Pressable
      onPress={() =>
        router.push({ pathname: "/ghostly-ticket/[id]", params: { id: id || subject, data: JSON.stringify(ticket) } })
      }
      className="bg-surface rounded-2xl px-4 py-3.5 mb-2 mx-4 active:opacity-70"
    >
      <View className="flex-row items-center justify-between mb-1">
        <Text className="text-[16px] font-semibold text-ink flex-1 mr-2" numberOfLines={1}>
          {subject}
        </Text>
        <View className={`rounded-full px-2.5 py-1 ${resolved ? "bg-go/15" : "bg-brand-soft"}`}>
          <Text className={`text-[11px] font-bold ${resolved ? "text-go" : "text-brand"}`}>{status.toUpperCase()}</Text>
        </View>
      </View>
      {email ? <Text className="text-[13px] text-muted mb-0.5">{email}</Text> : null}
      {message ? (
        <Text className="text-[14px] text-muted" numberOfLines={2}>
          {message}
        </Text>
      ) : null}
      {dateRaw ? <Text className="text-[11px] text-muted mt-1">{formatValue("created_at", dateRaw)}</Text> : null}
    </Pressable>
  );
}
