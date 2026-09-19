import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";
import { FlatList, Image, KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { API_URL, apiErrorMessage, getSupportThread, sendSupportMessage, type SupportMessageOut } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

type PickedImage = { uri: string; name: string; mimeType?: string };

export default function SupportScreen() {
  const token = useAuthStore((s) => s.token);
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");
  const [image, setImage] = useState<PickedImage | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: messages, isLoading, isError, refetch } = useQuery({
    queryKey: ["support-thread"],
    queryFn: getSupportThread,
  });

  async function pickImage() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.7 });
    if (res.canceled || !res.assets?.[0]) return;
    const asset = res.assets[0];
    setImage({ uri: asset.uri, name: "screenshot.jpg", mimeType: asset.mimeType ?? "image/jpeg" });
  }

  async function onSend() {
    const trimmed = text.trim();
    if (trimmed.length < 5) {
      setError("Please write at least 5 characters.");
      return;
    }
    setError(null);
    setSending(true);
    try {
      await sendSupportMessage(trimmed, subject.trim() || undefined, image ?? undefined);
      setText("");
      setSubject("");
      setImage(null);
      queryClient.invalidateQueries({ queryKey: ["support-thread"] });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not send your message."));
    } finally {
      setSending(false);
    }
  }

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["bottom"]}>
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
          renderItem={({ item }) => <Bubble message={item} authToken={token} />}
          contentContainerStyle={{ padding: 16, paddingBottom: 8 }}
        />
      )}

      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View className="px-4 pt-2 pb-3 border-t border-line bg-surface">
          {error ? <Text className="text-danger text-[12px] mb-1">{error}</Text> : null}

          <TextInput
            value={subject}
            onChangeText={setSubject}
            placeholder="Subject (optional)"
            placeholderTextColor="#8E8E93"
            className="bg-background rounded-xl px-3 py-2 text-ink text-[13px] mb-2"
          />

          {image ? (
            <View className="flex-row items-center mb-2">
              <Image source={{ uri: image.uri }} style={{ width: 44, height: 44, borderRadius: 8 }} />
              <Pressable onPress={() => setImage(null)} className="ml-2">
                <Text className="text-danger text-[13px] font-semibold">Remove</Text>
              </Pressable>
            </View>
          ) : null}

          <View className="flex-row items-end gap-2">
            <Pressable
              onPress={pickImage}
              className="bg-background rounded-2xl items-center justify-center"
              style={{ width: 44, height: 44 }}
            >
              <Text className="text-xl">📎</Text>
            </Pressable>
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

function Bubble({ message, authToken }: { message: SupportMessageOut; authToken: string | null }) {
  const isMine = message.direction === "in";
  // A local-disk image_url is a relative, auth-protected API path (Cloudinary's own signed
  // URL is already absolute and needs no auth header) - Image doesn't share axios's
  // interceptors, so the token is attached explicitly via the source's headers field.
  const imageSource = message.image_url
    ? message.image_url.startsWith("http")
      ? { uri: message.image_url }
      : { uri: `${API_URL}${message.image_url}`, headers: { Authorization: `Bearer ${authToken}` } }
    : null;

  return (
    <View className={`mb-3 max-w-[85%] ${isMine ? "self-end items-end" : "self-start items-start"}`}>
      <View className={`rounded-2xl px-4 py-3 ${isMine ? "bg-brand" : "bg-surface border border-line"}`}>
        {message.subject ? (
          <Text className={`text-[12px] font-bold mb-1 ${isMine ? "text-white" : "text-ink"}`}>
            {message.subject}
          </Text>
        ) : null}
        {imageSource ? (
          <Image
            source={imageSource}
            style={{ width: 180, height: 180, borderRadius: 10, marginBottom: message.text ? 8 : 0 }}
            resizeMode="cover"
          />
        ) : null}
        {message.text ? (
          <Text className={`text-[15px] ${isMine ? "text-white" : "text-ink"}`}>{message.text}</Text>
        ) : null}
      </View>
      <Text className="text-muted text-[11px] mt-1">
        {new Date(message.created_at).toLocaleString("en-IN", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Kolkata",
        })}
      </Text>
    </View>
  );
}
