import { BottomSheetBackdrop, BottomSheetModal, BottomSheetTextInput, BottomSheetView } from "@gorhom/bottom-sheet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Directory, Paths, File as ExpoFile } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useLocalSearchParams, useRouter } from "expo-router";
import { forwardRef, useCallback, useRef, useState } from "react";
import { ActivityIndicator, Linking, ScrollView, Switch, Text, View } from "react-native";

import { Badge, AccessBadge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { useToast } from "@/components/ui/Toast";
import {
  apiErrorMessage,
  blockUser,
  deleteUser,
  extendUser,
  getUser,
  messageUser,
  resumeUrl,
  unblockUser,
} from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function UserDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { show } = useToast();
  const token = useAuthStore((s) => s.token);

  const extendSheetRef = useRef<BottomSheetModal>(null);
  const messageSheetRef = useRef<BottomSheetModal>(null);
  const deleteSheetRef = useRef<BottomSheetModal>(null);

  const { data, isLoading } = useQuery({ queryKey: ["user", userId], queryFn: () => getUser(userId) });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["user", userId] });
    queryClient.invalidateQueries({ queryKey: ["users"] });
  };

  const blockMutation = useMutation({
    mutationFn: () => (data?.user.status === "blocked" ? unblockUser(userId) : blockUser(userId)),
    onSuccess: () => {
      show("Status update zala", "success");
      invalidate();
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteUser(userId),
    onSuccess: () => {
      show("User data delete zala", "success");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      router.back();
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const downloadResume = useCallback(async () => {
    try {
      const file = await ExpoFile.downloadFileAsync(resumeUrl(userId), new Directory(Paths.cache), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        idempotent: true,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri);
      } else {
        show(`Resume saved: ${file.uri}`, "success");
      }
    } catch (err) {
      show(apiErrorMessage(err, "Resume download zala nahi"), "error");
    }
  }, [userId, token, show]);

  if (isLoading || !data) {
    return (
      <View className="flex-1 bg-background items-center justify-center">
        <ActivityIndicator />
      </View>
    );
  }

  const { user, profile, payments, recent_deliveries, stats } = data;

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card className="mb-3">
          <Text className="text-xl font-extrabold text-ink">{user.full_name || "Unnamed"}</Text>
          <View className="flex-row items-center gap-2 mt-2">
            <StatusBadge status={user.status} />
            <AccessBadge access={user.access} />
          </View>

          <View className="flex-row gap-3 mt-4">
            {user.phone ? (
              <>
                <Button
                  label="📞 Call"
                  variant="ghost"
                  fullWidth={false}
                  onPress={() => Linking.openURL(`tel:${user.phone}`)}
                />
                <Button
                  label="💬 WhatsApp"
                  variant="ghost"
                  fullWidth={false}
                  onPress={() => Linking.openURL(`https://wa.me/${(user.phone ?? "").replace("+", "")}`)}
                />
              </>
            ) : null}
          </View>

          <View className="mt-3 gap-1">
            <InfoLine label="Phone" value={user.phone ?? "-"} />
            <InfoLine label="Telegram" value={user.username ? `@${user.username}` : "-"} />
            <InfoLine label="Language" value={user.language} />
            <InfoLine label="Joined" value={new Date(user.created_at).toLocaleDateString("en-IN")} />
            <InfoLine label="Access until" value={user.access_until ? new Date(user.access_until).toLocaleDateString("en-IN") : "-"} />
          </View>
        </Card>

        {profile ? (
          <Card className="mb-3">
            <Text className="text-sm font-bold text-ink mb-2">Profile</Text>
            <InfoLine label="Education" value={profile.education ?? "-"} />
            <InfoLine label="Course" value={profile.course ?? "-"} />
            <InfoLine label="Experience" value={`${profile.experience_years} years`} />
            <View className="flex-row flex-wrap mt-2">
              {profile.skills.map((s) => (
                <Badge key={s} label={s} tone="info" />
              ))}
            </View>
            {profile.has_resume ? (
              <View className="mt-3">
                <Button label="📄 Resume download" variant="ghost" onPress={downloadResume} />
              </View>
            ) : null}
          </Card>
        ) : null}

        <Card className="mb-3">
          <Text className="text-sm font-bold text-ink mb-2">Categories & types</Text>
          <View className="flex-row flex-wrap">
            {user.categories.map((c) => (
              <Badge key={c} label={c} tone="brand" />
            ))}
          </View>
        </Card>

        <Card className="mb-3">
          <Text className="text-sm font-bold text-ink mb-2">Jobs received ({stats.sent} sent, {stats.clicks} clicked)</Text>
          {recent_deliveries.length === 0 ? (
            <Text className="text-xs text-muted">Ajun kahi pathvle nahi.</Text>
          ) : (
            recent_deliveries.map((d, i) => (
              <View key={i} className="flex-row justify-between py-1.5 border-b border-line/40">
                <Text className="text-xs text-ink flex-1" numberOfLines={1}>
                  {d.title ?? `Job #${d.job_id}`}
                </Text>
                <Text className="text-xs text-muted">{d.clicked ? "✓ Clicked" : "Sent"}</Text>
              </View>
            ))
          )}
        </Card>

        <Card className="mb-3">
          <Text className="text-sm font-bold text-ink mb-2">Payments</Text>
          {payments.length === 0 ? (
            <Text className="text-xs text-muted">Kontihi payment nahi.</Text>
          ) : (
            payments.map((p) => (
              <View key={p.id} className="flex-row justify-between py-1.5 border-b border-line/40">
                <Text className="text-xs text-ink">₹{(p.amount_paise / 100).toFixed(0)}</Text>
                <Text className="text-xs text-muted">{p.status}</Text>
                <Text className="text-xs text-muted">{p.paid_at ? new Date(p.paid_at).toLocaleDateString("en-IN") : "-"}</Text>
              </View>
            ))
          )}
        </Card>

        <View className="gap-3 mt-2">
          <Button label="➕ Divas vadhva" variant="primary" onPress={() => extendSheetRef.current?.present()} />
          <Button label="✉️ Message pathva" variant="ghost" onPress={() => messageSheetRef.current?.present()} />
          <Button
            label={user.status === "blocked" ? "Unblock" : "⛔ Block"}
            variant={user.status === "blocked" ? "primary" : "danger"}
            onPress={() => blockMutation.mutate()}
            loading={blockMutation.isPending}
          />
          <Button label="🗑 Data delete" variant="danger" onPress={() => deleteSheetRef.current?.present()} />
        </View>
      </ScrollView>

      <ExtendSheet ref={extendSheetRef} userId={userId} onDone={invalidate} />
      <MessageSheet ref={messageSheetRef} userId={userId} />
      <ConfirmSheet
        ref={deleteSheetRef}
        title="Delete this user's data?"
        message="Profile, resume aani history kadhli jail. Payments record theva jail (accounting sathi)."
        confirmLabel="Delete permanently"
        onConfirm={() => {
          deleteMutation.mutate();
          deleteSheetRef.current?.dismiss();
        }}
      />
    </View>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between py-0.5">
      <Text className="text-xs text-muted">{label}</Text>
      <Text className="text-xs text-ink font-medium">{value}</Text>
    </View>
  );
}

const ExtendSheet = forwardRef<BottomSheetModal, { userId: number; onDone: () => void }>(function ExtendSheet(
  { userId, onDone },
  ref
) {
  const [days, setDays] = useState(30);
  const [custom, setCustom] = useState("");
  const [notify, setNotify] = useState(true);
  const [loading, setLoading] = useState(false);
  const { show } = useToast();

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  const submit = async () => {
    const value = custom ? parseInt(custom, 10) : days;
    if (!value || value <= 0) return;
    setLoading(true);
    try {
      await extendUser(userId, value, notify);
      show(`${value} divas vadhvle`, "success");
      onDone();
      (ref as React.RefObject<BottomSheetModal>).current?.dismiss();
    } catch (err) {
      show(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <BottomSheetModal ref={ref} snapPoints={["45%"]} backdropComponent={renderBackdrop}>
      <BottomSheetView className="px-5 pb-8 pt-2">
        <Text className="text-lg font-bold text-ink mb-4">Extend subscription</Text>
        <View className="flex-row flex-wrap mb-3">
          {[7, 15, 30].map((d) => (
            <Chip
              key={d}
              label={`${d} divas`}
              selected={days === d && !custom}
              onPress={() => {
                setDays(d);
                setCustom("");
              }}
            />
          ))}
        </View>
        <BottomSheetTextInput
          value={custom}
          onChangeText={setCustom}
          placeholder="Custom divas"
          keyboardType="number-pad"
          className="bg-background rounded-xl px-4 py-3 text-ink mb-4"
        />
        <View className="flex-row items-center justify-between mb-5">
          <Text className="text-sm text-ink">Student la notify kara</Text>
          <Switch value={notify} onValueChange={setNotify} />
        </View>
        <Button label="Confirm" onPress={submit} loading={loading} />
      </BottomSheetView>
    </BottomSheetModal>
  );
});

const MessageSheet = forwardRef<BottomSheetModal, { userId: number }>(function MessageSheet({ userId }, ref) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const { show } = useToast();

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  const submit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await messageUser(userId, text.trim());
      show(res.result === "ok" ? "Message pathvla" : `Result: ${res.result}`, res.result === "ok" ? "success" : "warn");
      setText("");
      (ref as React.RefObject<BottomSheetModal>).current?.dismiss();
    } catch (err) {
      show(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <BottomSheetModal ref={ref} snapPoints={["40%"]} backdropComponent={renderBackdrop}>
      <BottomSheetView className="px-5 pb-8 pt-2">
        <Text className="text-lg font-bold text-ink mb-4">Send a message</Text>
        <BottomSheetTextInput
          value={text}
          onChangeText={setText}
          placeholder="Type your message..."
          multiline
          className="bg-background rounded-xl px-4 py-3 text-ink mb-4 min-h-[80px]"
        />
        <Button label="Send" onPress={submit} loading={loading} />
      </BottomSheetView>
    </BottomSheetModal>
  );
});
