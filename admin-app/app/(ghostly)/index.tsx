import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card } from "@/components/ui/Card";
import { KeyValueList } from "@/components/ui/KeyValueList";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { apiErrorMessage } from "@/lib/api";
import { firstOfNumber } from "@/lib/ghostlyFormat";
import { getGhostlyStats, listGhostlySupport, listGhostlyUsers } from "@/lib/ghostlyApi";
import { useAppModeStore } from "@/store/appMode";

export default function GhostlyDashboard() {
  const insets = useSafeAreaInsets();
  const beginSwitch = useAppModeStore((s) => s.beginSwitch);

  const stats = useQuery({
    queryKey: ["ghostly-stats"],
    queryFn: getGhostlyStats,
    refetchInterval: 60_000,
  });

  const newToday = useQuery({
    queryKey: ["ghostly-users", "new_today"],
    queryFn: () => listGhostlyUsers({ filter: "new_today" }),
    refetchInterval: 60_000,
  });

  const support = useQuery({
    queryKey: ["ghostly-support-summary"],
    queryFn: listGhostlySupport,
    refetchInterval: 30_000,
  });

  const loading = stats.isLoading || newToday.isLoading || support.isLoading;
  const error = stats.error || newToday.error || support.error;

  const refreshing = stats.isFetching || newToday.isFetching || support.isFetching;
  const refresh = () => {
    stats.refetch();
    newToday.refetch();
    support.refetch();
  };

  const openTickets = (support.data ?? []).filter((t) => {
    const status = String(t.status ?? t.ticket_status ?? t.state ?? "open").toLowerCase();
    return status !== "resolved" && status !== "closed";
  }).length;

  const s = stats.data ?? {};
  // Confirmed field names from the live API (camelCase): totalUsers, proUsers, freeUsers,
  // blockedUsers, newUsersToday, newUsersThisWeek, activeToday, totalPlatformHours. The
  // snake_case candidates stay as a fallback in case the API ever changes shape.
  const totalUsers = firstOfNumber(s, ["totalUsers", "total_users", "users_total", "total"]);
  const proUsers = firstOfNumber(s, ["proUsers", "pro_users", "paid_users", "pro_count"]);
  const blockedUsers = firstOfNumber(s, ["blockedUsers", "blocked_users", "blocked_count"]);
  const activeToday = firstOfNumber(s, ["activeToday", "active_today"]);

  const knownStatKeys = [
    "totalUsers",
    "total_users",
    "users_total",
    "total",
    "proUsers",
    "pro_users",
    "paid_users",
    "pro_count",
    "blockedUsers",
    "blocked_users",
    "blocked_count",
    "activeToday",
    "active_today",
  ];
  const restOfStats = Object.fromEntries(Object.entries(s).filter(([k]) => !knownStatKeys.includes(k)));

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor="#EA580C" />}
    >
      <View className="px-4 pt-2 pb-3 flex-row items-center justify-between">
        <View>
          <Text className="text-[32px] font-bold text-ink tracking-tight">👻 GhostlyAI.in</Text>
          <Text className="text-[15px] text-muted mt-0.5">Sister app · admin data</Text>
        </View>
        <Text
          onPress={() => beginSwitch("jobalert")}
          className="text-brand text-[13px] font-semibold bg-brand-soft rounded-full px-3 py-2"
        >
          🏠 Job Alert Bot
        </Text>
      </View>

      {error ? (
        <Card className="mx-4 mb-3 bg-danger/10">
          <Text className="text-danger font-semibold mb-1">Could not load GhostlyAI.in data</Text>
          <Text className="text-danger text-[13px]">{apiErrorMessage(error)}</Text>
          <Text className="text-muted text-[12px] mt-2">
            If this says the API key was rejected, the upstream auth header name in the backend's
            GHOSTLY_API_AUTH_HEADER setting probably needs updating.
          </Text>
        </Card>
      ) : null}

      {loading ? (
        <View className="px-4">
          <ListSkeleton count={3} />
        </View>
      ) : (
        <>
          <View className="flex-row flex-wrap gap-3 px-4 mb-3">
            <StatCard label="Total users" value={totalUsers} icon="👤" delay={0} onPress={() => router.push("/(ghostly)/users")} />
            <StatCard
              label="New today"
              value={newToday.data?.length ?? 0}
              icon="✨"
              delay={20}
              highlight
              onPress={() => router.push({ pathname: "/(ghostly)/users", params: { filter: "new_today" } })}
            />
            <StatCard label="Pro users" value={proUsers} icon="⭐" delay={40} />
            <StatCard label="Blocked" value={blockedUsers} icon="🚫" delay={60} />
            <StatCard label="Active today" value={activeToday} icon="⚡" delay={70} />
          </View>

          <View className="px-4 mb-1 flex-row">
            <StatCard
              label="Support tickets waiting for a reply"
              value={openTickets}
              icon="💬"
              highlight={openTickets > 0}
              delay={80}
              onPress={() => router.push("/(ghostly)/tickets")}
            />
          </View>

          {Object.keys(restOfStats).length > 0 ? (
            <View className="px-4 mt-2">
              <KeyValueList data={restOfStats} title="All stats from GhostlyAI.in" />
            </View>
          ) : null}

          <View className="px-4 mt-1">
            <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">
              New signups today ({newToday.data?.length ?? 0})
            </Text>
            {(newToday.data ?? []).length === 0 ? (
              <Card className="mb-3">
                <Text className="text-muted text-center py-2">No new signups yet today</Text>
              </Card>
            ) : (
              <Card className="mb-3">
                {(newToday.data ?? []).slice(0, 5).map((u, i) => {
                  const name = String(u.name ?? u.full_name ?? u.username ?? "Unnamed");
                  const email = String(u.email ?? u.email_address ?? "");
                  return (
                    <View key={String(u.id ?? u._id ?? i)} className={i > 0 ? "mt-3 pt-3 border-t border-line" : ""}>
                      <Text className="text-[16px] font-semibold text-ink">{name}</Text>
                      {email ? <Text className="text-[13px] text-muted">{email}</Text> : null}
                    </View>
                  );
                })}
                {(newToday.data ?? []).length > 5 ? (
                  <Text
                    onPress={() => router.push({ pathname: "/(ghostly)/users", params: { filter: "new_today" } })}
                    className="text-brand text-[13px] font-semibold mt-3 pt-3 border-t border-line text-center"
                  >
                    View all {newToday.data?.length} →
                  </Text>
                ) : null}
              </Card>
            )}
          </View>
        </>
      )}
    </ScrollView>
  );
}
