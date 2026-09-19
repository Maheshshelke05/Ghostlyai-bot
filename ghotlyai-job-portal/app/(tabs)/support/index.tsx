import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage, getSupportThread, sendSupportMessage, type SupportMessageOut } from "@/lib/api";

export default function SupportScreen() {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: messages, isLoading, isError, refetch } = useQuery({
    queryKey: ["support-thread"],
    queryFn: getSupportThread,
  });

  async function onSend() {
    const trimmed = text.trim();
    if (trimmed.length < 5) {
      setError("Please write at least 5 characters.");
      return;
    }
    setError(null);
    setSending(true);
    try {
      await sendSupportMessage(trimmed);
      setText("");
      queryClient.invalidateQueries({ queryKey: ["support-thread"] });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not send your message."));
    } finally {
      setSending(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <View className="px-4 pt-3 pb-2">
        <Text className="font-display text-ink text-[24px]">Support</Text>
        <Text className="font-body text-muted text-[14px] mt-1">
          Have a question or found a problem? Message us here.
        </Text>
      </View>

      {isLoading ? (
        <ListSkeleton />
      ) : isError ? (
        <View className="items-center py-10 px-6">
          <Text className="text-muted text-center mb-4">Couldn't load your messages.</Text>
          <View className="w-40">
            <Button label="Retry" onPress={() => refetch()} variant="brand" />
          </View>
        </View>
      ) : !messages || messages.length === 0 ? (
        <EmptyState emoji="💬" title="No messages yet. Send us one below and we'll reply here." />
      ) : (
        <FlatList
          data={messages}
          keyExtractor={(m) => String(m.id)}
          renderItem={({ item }) => <Bubble message={item} />}
          contentContainerStyle={{ padding: 16, paddingBottom: 8 }}
          inverted={false}
        />
      )}

      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View className="px-4 pt-2 pb-3 border-t border-line bg-surface">
          {error ? <Text className="text-danger text-[12px] mb-1">{error}</Text> : null}
          <View className="flex-row items-end gap-2">
            <TextInput
              value={text}
              onChangeText={setText}
              placeholder="Type your message..."
              placeholderTextColor="#8E8E93"
              multiline
              className="flex-1 bg-background rounded-2xl px-4 py-3 text-ink text-[15px]"
              style={{ maxHeight: 100 }}
            />
            <View style={{ width: 84 }}>
              <Button label="Send" onPress={onSend} loading={sending} disabled={text.trim().length === 0} />
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Bubble({ message }: { message: SupportMessageOut }) {
  const isMine = message.direction === "in";
  return (
    <View className={`mb-3 max-w-[85%] ${isMine ? "self-end items-end" : "self-start items-start"}`}>
      <View className={`rounded-2xl px-4 py-3 ${isMine ? "bg-brand" : "bg-surface border border-line"}`}>
        <Text className={`text-[15px] ${isMine ? "text-white" : "text-ink"}`}>{message.text}</Text>
      </View>
      <Text className="text-muted text-[11px] mt-1">
        {new Date(message.created_at).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
      </Text>
    </View>
  );
}
