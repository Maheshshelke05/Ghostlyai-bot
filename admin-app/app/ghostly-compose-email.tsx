import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useMutation } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api";
import { sendGhostlyEmail } from "@/lib/ghostlyApi";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function GhostlyComposeEmailScreen() {
  const { to: toParam } = useLocalSearchParams<{ to?: string }>();
  const { show } = useToast();
  const sheetRef = useRef<BottomSheetModal>(null);
  const [to, setTo] = useState(toParam ?? "");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const mutation = useMutation({
    mutationFn: () => sendGhostlyEmail(to.trim(), subject.trim(), body.trim()),
    onSuccess: () => {
      show("Email sent", "success");
      router.back();
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const validTo = EMAIL_RE.test(to.trim());
  const canSend = validTo && subject.trim().length > 0 && body.trim().length > 0;

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Text className="text-sm font-semibold text-muted mb-1.5">To</Text>
        <TextInput
          value={to}
          onChangeText={setTo}
          placeholder="student@example.com"
          placeholderTextColor="#8E8E93"
          autoCapitalize="none"
          keyboardType="email-address"
          className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-1"
        />
        {to.length > 0 && !validTo ? <Text className="text-danger text-xs mb-2">Enter a valid email</Text> : <View className="mb-3" />}

        <Text className="text-sm font-semibold text-muted mb-1.5">Subject</Text>
        <TextInput
          value={subject}
          onChangeText={setSubject}
          placeholder="Subject"
          placeholderTextColor="#8E8E93"
          maxLength={300}
          className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-3"
        />

        <Text className="text-sm font-semibold text-muted mb-1.5">Message</Text>
        <TextInput
          value={body}
          onChangeText={setBody}
          placeholder="Type the email body…"
          placeholderTextColor="#8E8E93"
          multiline
          maxLength={20000}
          className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-4"
          style={{ minHeight: 160, textAlignVertical: "top" }}
        />

        <Button
          label="Send email"
          variant="primary"
          disabled={!canSend}
          loading={mutation.isPending}
          onPress={() => sheetRef.current?.present()}
        />
      </ScrollView>

      <ConfirmSheet
        ref={sheetRef}
        title="Send this email?"
        message={`To: ${to.trim()}`}
        confirmLabel="Send"
        danger={false}
        onConfirm={() => {
          sheetRef.current?.dismiss();
          mutation.mutate();
        }}
      />
    </View>
  );
}
