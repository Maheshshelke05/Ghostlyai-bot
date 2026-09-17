import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { RefreshControl, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api";
import { firstOfBool, firstOfNumber, firstOfString, stripHtml, type AnyRecord } from "@/lib/ghostlyFormat";
import { createGhostlyAnnouncement, listGhostlyAnnouncements, sendGhostlyAnnouncement } from "@/lib/ghostlyApi";

function isSent(a: AnyRecord): boolean {
  // Confirmed live shape: {message, sent_at, sent_count, id, target, title} - no status/sent
  // field, so a present sent_at is the real signal. status/sent stay as a fallback in case a
  // draft (not-yet-sent) announcement has a different shape than the sent ones seen so far.
  const sentAt = firstOfString(a, ["sent_at", "sentAt"]);
  if (sentAt) return true;
  const status = firstOfString(a, ["status"], "").toLowerCase();
  if (status) return status === "sent" || status === "completed";
  return firstOfBool(a, ["sent"]) ?? false;
}

export default function GhostlyAnnouncementsScreen() {
  const insets = useSafeAreaInsets();
  const { show } = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [pendingSend, setPendingSend] = useState<AnyRecord | null>(null);
  const sendSheetRef = useRef<BottomSheetModal>(null);

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ["ghostly-announcements"],
    queryFn: listGhostlyAnnouncements,
  });

  const createMutation = useMutation({
    mutationFn: () => createGhostlyAnnouncement(title.trim(), body.trim()),
    onSuccess: () => {
      setTitle("");
      setBody("");
      queryClient.invalidateQueries({ queryKey: ["ghostly-announcements"] });
      show("Draft saved below", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const sendMutation = useMutation({
    mutationFn: (announcementId: string) => sendGhostlyAnnouncement(announcementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ghostly-announcements"] });
      show("Announcement sent to all users", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const announcements = data ?? [];

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top }}>
      <ScreenHeader title="Announcements" subtitle={`${announcements.length} total`} />
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={isFetching} onRefresh={refetch} tintColor="#EA580C" />}
      >
        <Card className="mb-4">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">New announcement</Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="Title"
            placeholderTextColor="#8E8E93"
            maxLength={200}
            className="bg-background border border-line rounded-2xl px-4 py-3 text-ink mb-2"
          />
          <TextInput
            value={body}
            onChangeText={setBody}
            placeholder="Message body"
            placeholderTextColor="#8E8E93"
            multiline
            maxLength={20000}
            className="bg-background border border-line rounded-2xl px-4 py-3 text-ink mb-2"
            style={{ minHeight: 90, textAlignVertical: "top" }}
          />
          <Text className="text-[12px] text-muted mb-2">
            Saving with the same title within 5 minutes reuses the earlier draft instead of duplicating it.
          </Text>
          <Button
            label="Save draft"
            variant="brand"
            disabled={!title.trim() || !body.trim()}
            loading={createMutation.isPending}
            onPress={() => createMutation.mutate()}
          />
        </Card>

        {error ? (
          <View className="mb-3 bg-danger/10 rounded-2xl p-3">
            <Text className="text-danger text-[13px]">{apiErrorMessage(error)}</Text>
          </View>
        ) : null}

        {isLoading ? (
          <ListSkeleton />
        ) : announcements.length === 0 ? (
          <EmptyState emoji="📣" title="No announcements yet." />
        ) : (
          announcements.map((a, i) => {
            const id = firstOfString(a, ["id", "_id", "announcement_id"], String(i));
            const sent = isSent(a);
            const sentTo = firstOfNumber(a, ["sent_to", "recipients", "sent_count"], -1);
            return (
              <Card key={id} className="mb-3">
                <View className="flex-row items-center justify-between mb-1">
                  <Text className="text-[16px] font-bold text-ink flex-1 mr-2">{firstOfString(a, ["title"], "Untitled")}</Text>
                  <View className={`rounded-full px-2.5 py-1 ${sent ? "bg-go/15" : "bg-line"}`}>
                    <Text className={`text-[11px] font-bold ${sent ? "text-go" : "text-muted"}`}>{sent ? "SENT" : "DRAFT"}</Text>
                  </View>
                </View>
                <Text className="text-[14px] text-muted mb-2" numberOfLines={3}>
                  {stripHtml(firstOfString(a, ["message", "body"], ""))}
                </Text>
                {sent && sentTo >= 0 ? <Text className="text-[12px] text-muted mb-2">Sent to {sentTo} users</Text> : null}
                {!sent ? (
                  <Button
                    label="Send to all users"
                    variant="primary"
                    loading={sendMutation.isPending && pendingSend === a}
                    onPress={() => {
                      setPendingSend(a);
                      sendSheetRef.current?.present();
                    }}
                  />
                ) : null}
              </Card>
            );
          })
        )}
      </ScrollView>

      <ConfirmSheet
        ref={sendSheetRef}
        title="Send this announcement to all users?"
        message={pendingSend ? firstOfString(pendingSend, ["title"], "") : undefined}
        confirmLabel="Send to everyone"
        danger
        onConfirm={() => {
          sendSheetRef.current?.dismiss();
          const id = pendingSend ? firstOfString(pendingSend, ["id", "_id", "announcement_id"]) : "";
          if (id) sendMutation.mutate(id);
        }}
      />
    </View>
  );
}
