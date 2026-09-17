import { BottomSheetBackdrop, BottomSheetModal } from "@gorhom/bottom-sheet";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { useToast } from "@/components/ui/Toast";
import {
  apiErrorMessage,
  createBroadcast,
  getBroadcast,
  listCategories,
  previewBroadcastCount,
  type Audience,
} from "@/lib/api";

const AUDIENCES: { value: Audience; label: string }[] = [
  { value: "all", label: "All active" },
  { value: "paid", label: "Paid" },
  { value: "trial", label: "Trial" },
  { value: "expired", label: "Expired" },
];

export default function BroadcastScreen() {
  const { show } = useToast();
  const confirmRef = useRef<BottomSheetModal>(null);
  const [text, setText] = useState("");
  const [audience, setAudience] = useState<Audience>("all");
  const [categoryId, setCategoryId] = useState<number | undefined>(undefined);
  const [count, setCount] = useState<number | null>(null);
  const [loadingCount, setLoadingCount] = useState(false);
  const [broadcastId, setBroadcastId] = useState<number | null>(null);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  const { data: progress } = useQuery({
    queryKey: ["broadcast", broadcastId],
    queryFn: () => getBroadcast(broadcastId!),
    enabled: broadcastId !== null,
    refetchInterval: (query) => (query.state.data?.status === "done" ? false : 1500),
  });

  useEffect(() => {
    let cancelled = false;
    setLoadingCount(true);
    previewBroadcastCount(audience, categoryId)
      .then((c) => !cancelled && setCount(c))
      .catch(() => !cancelled && setCount(null))
      .finally(() => !cancelled && setLoadingCount(false));
    return () => {
      cancelled = true;
    };
  }, [audience, categoryId]);

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  const send = async () => {
    try {
      const res = await createBroadcast(text.trim(), audience, categoryId);
      setBroadcastId(res.id);
      show("Broadcast queued", "success");
    } catch (err) {
      show(apiErrorMessage(err), "error");
    }
  };

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Text className="text-sm font-semibold text-muted mb-1.5">Audience</Text>
        <View className="flex-row flex-wrap mb-2">
          {AUDIENCES.map((a) => (
            <Chip key={a.value} label={a.label} selected={audience === a.value} onPress={() => setAudience(a.value)} />
          ))}
        </View>

        <Text className="text-sm font-semibold text-muted mb-1.5 mt-2">Category (optional)</Text>
        <View className="flex-row flex-wrap mb-3">
          <Chip label="All categories" selected={categoryId === undefined} onPress={() => setCategoryId(undefined)} />
          {(categories ?? []).map((c) => (
            <Chip key={c.id} label={c.name} selected={categoryId === c.id} onPress={() => setCategoryId(c.id)} />
          ))}
        </View>

        <Text className="text-sm font-semibold text-muted mb-1.5">Message</Text>
        <TextInput
          value={text}
          onChangeText={setText}
          multiline
          maxLength={4000}
          placeholder="Type your broadcast message (HTML tags like <b> allowed)"
          className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-1"
          style={{ minHeight: 120, textAlignVertical: "top" }}
        />
        <Text className="text-xs text-muted mb-3 text-right">{text.length}/4000</Text>

        {text.trim() ? (
          <View className="bg-[#DCF8C6] rounded-2xl rounded-tr-sm p-3 mb-4 self-end max-w-[85%]">
            <Text className="text-ink">{text}</Text>
          </View>
        ) : null}

        <Text className="text-sm text-muted mb-4">
          {loadingCount ? "Counting..." : `This message will go to ${count ?? 0} ${count === 1 ? "student" : "students"}`}
        </Text>

        <Button
          label="Send broadcast"
          variant="primary"
          disabled={!text.trim() || (count ?? 0) === 0}
          onPress={() => confirmRef.current?.present()}
        />

        {progress ? (
          <View className="mt-6 bg-surface border border-line/60 rounded-2xl p-4">
            <Text className="text-sm font-bold text-ink mb-2">
              Status: {progress.status} ({progress.sent}/{progress.total} sent, {progress.failed} failed)
            </Text>
          </View>
        ) : null}
      </ScrollView>

      <ConfirmSheet
        ref={confirmRef}
        title="Send this broadcast?"
        message={`This will message ${count ?? 0} students. Avoid sending more than 2 broadcasts a week.`}
        confirmLabel="Send"
        danger={false}
        onConfirm={() => {
          confirmRef.current?.dismiss();
          send();
        }}
      />
    </View>
  );
}
