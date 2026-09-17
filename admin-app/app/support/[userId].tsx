import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, getSupportThread, replySupport, type SupportMessageOut } from "@/lib/api";

function stamp(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" })} · ${d.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

export default function SupportThreadScreen() {
  const { userId } = useLocalSearchParams<{ userId: string }>();
  const id = Number(userId);
  const queryClient = useQueryClient();
  const insets = useSafeAreaInsets();
  const { show } = useToast();
  const scrollRef = useRef<ScrollView>(null);
  const [text, setText] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["support-thread", id],
    queryFn: () => getSupportThread(id),
    refetchInterval: 15_000,
  });

  useEffect(() => {
    if (data) setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
  }, [data]);

  const reply = useMutation({
    mutationFn: () => replySupport(id, text.trim()),
    onSuccess: (res) => {
      setText("");
      queryClient.invalidateQueries({ queryKey: ["support-thread", id] });
      queryClient.invalidateQueries({ queryKey: ["support"] });
      if (res.result === "ok") show("Reply sent", "success");
      else if (res.result === "blocked") show("Saved, but the student has blocked the bot", "warn");
      else show("Saved, but Telegram could not deliver it", "warn");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  if (isLoading || !data) {
    return (
      <View className="flex-1 bg-background items-center justify-center">
        <ActivityIndicator />
      </View>
    );
  }

  const name = data.user.full_name || data.user.username || `User #${data.user.id}`;

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-background"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 88 : 0}
    >
      <Pressable
        onPress={() => router.push(`/users/${data.user.id}`)}
        className="bg-surface px-4 py-3 flex-row items-center border-b border-line"
      >
        <View className="w-9 h-9 rounded-full bg-brand-soft items-center justify-center mr-3">
          <Text className="text-brand font-bold">{name.trim().charAt(0).toUpperCase()}</Text>
        </View>
        <View className="flex-1">
          <Text className="text-[16px] font-semibold text-ink">{name}</Text>
          <Text className="text-xs text-muted">
            {data.user.phone ?? "no phone"} · {data.user.language.toUpperCase()} · tap to open profile
          </Text>
        </View>
      </Pressable>

      <ScrollView
        ref={scrollRef}
        className="flex-1"
        contentContainerStyle={{ padding: 16, paddingBottom: 12 }}
        keyboardShouldPersistTaps="handled"
      >
        {data.messages.map((m) => (
          <Bubble key={m.id} message={m} />
        ))}
      </ScrollView>

      <View
        className="bg-surface border-t border-line px-3 pt-2 flex-row items-end"
        style={{ paddingBottom: Math.max(insets.bottom, 10) }}
      >
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Write a reply…"
          placeholderTextColor="#8E8E93"
          multiline
          maxLength={4000}
          className="flex-1 bg-background rounded-[20px] px-4 py-2.5 text-[16px] text-ink"
          style={{ maxHeight: 120 }}
        />
        <Pressable
          disabled={!text.trim() || reply.isPending}
          onPress={() => reply.mutate()}
          className={`ml-2 w-10 h-10 rounded-full items-center justify-center ${text.trim() ? "bg-brand" : "bg-line"}`}
        >
          {reply.isPending ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text className="text-white text-lg font-bold">↑</Text>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function Bubble({ message }: { message: SupportMessageOut }) {
  const mine = message.direction === "out";
  return (
    <View className={`mb-2 max-w-[82%] ${mine ? "self-end" : "self-start"}`}>
      <View className={`px-3.5 py-2.5 ${mine ? "bg-brand rounded-[18px] rounded-br-md" : "bg-surface rounded-[18px] rounded-bl-md"}`}>
        <Text className={`text-[16px] ${mine ? "text-white" : "text-ink"}`}>{message.text}</Text>
      </View>
      <Text className={`text-[11px] text-muted mt-1 ${mine ? "text-right mr-1" : "ml-1"}`}>{stamp(message.created_at)}</Text>
    </View>
  );
}
