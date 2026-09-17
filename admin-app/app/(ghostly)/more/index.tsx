import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { ActivityIndicator, RefreshControl, ScrollView, Switch, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { KeyValueList } from "@/components/ui/KeyValueList";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api";
import { firstOfBool, firstOfKey, firstOfNumber } from "@/lib/ghostlyFormat";
import { getGhostlyConfig, getGhostlyEmailStats, updateGhostlyConfig } from "@/lib/ghostlyApi";
import { useAuthStore } from "@/store/auth";
import { useAppModeStore } from "@/store/appMode";

export default function GhostlyMoreScreen() {
  const insets = useSafeAreaInsets();
  const { show } = useToast();
  const queryClient = useQueryClient();
  const setMode = useAppModeStore((s) => s.setMode);
  const logout = useAuthStore((s) => s.logout);
  const admin = useAuthStore((s) => s.admin);

  const emailStats = useQuery({ queryKey: ["ghostly-email-stats"], queryFn: getGhostlyEmailStats });
  const config = useQuery({ queryKey: ["ghostly-config"], queryFn: getGhostlyConfig });

  const aiKey = firstOfKey(config.data, ["ai_auto_reply", "auto_reply", "ai_autoreply"]);
  const aiEnabled = firstOfBool(config.data, ["ai_auto_reply", "auto_reply", "ai_autoreply"]) ?? false;

  const toggleAi = useMutation({
    mutationFn: (value: boolean) => updateGhostlyConfig({ [aiKey]: value }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["ghostly-config"], updated);
      show("AI auto-reply updated", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const e = emailStats.data ?? {};
  const totalSent = firstOfNumber(e, ["total_sent", "sent_total", "total"]);
  const sentToday = firstOfNumber(e, ["sent_today", "today_sent"]);
  const opened = firstOfNumber(e, ["opened", "opens", "open_count"]);
  const clicked = firstOfNumber(e, ["clicked", "clicks", "click_count"]);
  const knownEmailKeys = ["total_sent", "sent_total", "total", "sent_today", "today_sent", "opened", "opens", "open_count", "clicked", "clicks", "click_count"];
  const restEmail = Object.fromEntries(Object.entries(e).filter(([k]) => !knownEmailKeys.includes(k)));

  const refreshing = emailStats.isFetching || config.isFetching;

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: 40 }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            emailStats.refetch();
            config.refetch();
          }}
          tintColor="#EA580C"
        />
      }
    >
      <ScreenHeader title="More" subtitle={`${admin?.name ?? ""} · GhostlyAI.in`} />

      <View className="px-4">
        <Card className="mb-3">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">Email</Text>
          {emailStats.isLoading ? (
            <ActivityIndicator />
          ) : emailStats.error ? (
            <Text className="text-danger text-[13px]">{apiErrorMessage(emailStats.error)}</Text>
          ) : (
            <View className="flex-row flex-wrap">
              <Stat label="Total sent" value={totalSent} />
              <Stat label="Sent today" value={sentToday} />
              <Stat label="Opened" value={opened} />
              <Stat label="Clicked" value={clicked} />
            </View>
          )}
          <View className="mt-3">
            <Button label="✉️ Send custom email" variant="brand" onPress={() => router.push("/ghostly-compose-email")} />
          </View>
        </Card>

        {Object.keys(restEmail).length > 0 ? <KeyValueList data={restEmail} title="Other email stats" /> : null}

        <Card className="mb-3">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">AI auto-reply</Text>
          <View className="flex-row items-center justify-between">
            <Text className="text-[16px] text-ink flex-1 mr-3">Automatically answer support tickets with AI</Text>
            {config.isLoading ? (
              <ActivityIndicator />
            ) : (
              <Switch
                value={aiEnabled}
                onValueChange={(v) => toggleAi.mutate(v)}
                disabled={toggleAi.isPending}
                trackColor={{ false: "#E5E5EA", true: "#EA580C" }}
                thumbColor="#FFFFFF"
              />
            )}
          </View>
          {config.error ? <Text className="text-danger text-[13px] mt-2">{apiErrorMessage(config.error)}</Text> : null}
        </Card>

        <Card className="mb-3">
          <Button
            label="🏠 Switch to Job Alert Bot"
            variant="ghost"
            onPress={() => {
              setMode("jobalert");
              show("Switched to Job Alert Bot", "success");
            }}
          />
        </Card>

        <Card>
          <Button label="Log out" variant="danger" onPress={logout} />
        </Card>
      </View>
    </ScrollView>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <View className="w-1/2 mb-2">
      <Text className="text-[20px] font-bold text-ink">{value.toLocaleString("en-IN")}</Text>
      <Text className="text-[12px] text-muted">{label}</Text>
    </View>
  );
}
