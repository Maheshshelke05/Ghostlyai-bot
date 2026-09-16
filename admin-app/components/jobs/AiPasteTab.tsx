import * as Clipboard from "expo-clipboard";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { aiParseJobs, apiErrorMessage } from "@/lib/api";
import { useAiDraftsStore } from "@/store/aiDrafts";

const MAX_CHARS = 15_000;

export function AiPasteTab() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const { show } = useToast();
  const setDrafts = useAiDraftsStore((s) => s.setDrafts);

  const pasteFromClipboard = async () => {
    const clip = await Clipboard.getStringAsync();
    if (clip) setText(clip.slice(0, MAX_CHARS));
  };

  const extract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const drafts = await aiParseJobs(text.slice(0, MAX_CHARS));
      if (drafts.length === 0) {
        show("Kontihi job sapadli nahi. Text tapasun parat try kara.", "warn");
        return;
      }
      setDrafts(drafts);
      router.push("/jobs/ai-review");
    } catch (err) {
      show(apiErrorMessage(err, "AI parsing fail zali"), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="p-4 flex-1">
      <View className="flex-row justify-between items-center mb-2">
        <Text className="text-sm font-semibold text-muted">WhatsApp / website text paste kara</Text>
        <Pressable onPress={pasteFromClipboard}>
          <Text className="text-info text-sm font-semibold">📋 Paste</Text>
        </Pressable>
      </View>

      <TextInput
        value={text}
        onChangeText={(t) => setText(t.slice(0, MAX_CHARS))}
        multiline
        placeholder="WhatsApp / website varcha job text ithe paste kara"
        className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink flex-1"
        style={{ textAlignVertical: "top", minHeight: 220 }}
      />
      <Text className="text-xs text-muted text-right mt-1">
        {text.length} / {MAX_CHARS}
      </Text>

      <View className="mt-4">
        <Button label="🤖 Jobs kadha" onPress={extract} loading={loading} variant="brand" disabled={!text.trim()} />
      </View>

      {loading ? (
        <View className="items-center mt-6">
          <ActivityIndicator />
          <Text className="text-muted text-sm mt-2">AI jobs shodhtoy...</Text>
        </View>
      ) : null}
    </View>
  );
}
