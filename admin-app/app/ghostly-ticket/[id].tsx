import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { KeyValueList } from "@/components/ui/KeyValueList";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api";
import { firstOfString, formatValue, type AnyRecord } from "@/lib/ghostlyFormat";
import { replyGhostlySupport, updateGhostlySupportStatus } from "@/lib/ghostlyApi";

function statusOf(t: AnyRecord): string {
  return firstOfString(t, ["status", "ticket_status", "state"], "open").toLowerCase();
}

export default function GhostlyTicketDetailScreen() {
  const { id, data } = useLocalSearchParams<{ id: string; data?: string }>();
  const queryClient = useQueryClient();
  const { show } = useToast();
  const replySheetRef = useRef<BottomSheetModal>(null);
  const reopenSheetRef = useRef<BottomSheetModal>(null);

  let ticket: AnyRecord = {};
  try {
    ticket = data ? JSON.parse(data) : {};
  } catch {
    ticket = {};
  }

  const [status, setStatus] = useState(statusOf(ticket));
  const resolved = status === "resolved" || status === "closed";
  const [replyText, setReplyText] = useState("");

  const subject = firstOfString(ticket, ["subject", "title"], "Support request");
  const email = firstOfString(ticket, ["email", "user_email"]);
  const category = firstOfString(ticket, ["category"]);
  const message = firstOfString(ticket, ["message", "description", "body"]);
  const steps = firstOfString(ticket, ["steps_to_reproduce", "steps"]);
  const appVersion = firstOfString(ticket, ["app_version", "version"]);
  const dateRaw = firstOfString(ticket, ["created_at", "date", "timestamp"]);

  const shownKeys = [
    "id", "_id", "ticket_id", "subject", "title", "email", "user_email", "category", "message",
    "description", "body", "steps_to_reproduce", "steps", "app_version", "version", "status",
    "ticket_status", "state", "created_at", "date", "timestamp",
  ];
  const rest = Object.fromEntries(Object.entries(ticket).filter(([k]) => !shownKeys.includes(k.toLowerCase())));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["ghostly-support"] });
    queryClient.invalidateQueries({ queryKey: ["ghostly-support-summary"] });
  };

  const replyMutation = useMutation({
    mutationFn: () => replyGhostlySupport(id, replyText.trim(), true),
    onSuccess: () => {
      setStatus("resolved");
      setReplyText("");
      invalidate();
      show("Reply sent and ticket resolved", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const reopenMutation = useMutation({
    mutationFn: () => updateGhostlySupportStatus(id, "reopened"),
    onSuccess: () => {
      setStatus("reopened");
      invalidate();
      show("Ticket reopened", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  return (
    <KeyboardAvoidingView className="flex-1 bg-background" behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
        <Card className="mb-3">
          <View className="flex-row items-center justify-between mb-2">
            <Text className="text-[18px] font-bold text-ink flex-1 mr-2">{subject}</Text>
            <View className={`rounded-full px-2.5 py-1 ${resolved ? "bg-go/15" : "bg-brand-soft"}`}>
              <Text className={`text-[11px] font-bold ${resolved ? "text-go" : "text-brand"}`}>{status.toUpperCase()}</Text>
            </View>
          </View>
          {email ? <Text className="text-[14px] text-muted mb-0.5">{email}</Text> : null}
          {category ? <Text className="text-[13px] text-muted mb-0.5">Category: {category}</Text> : null}
          {appVersion ? <Text className="text-[13px] text-muted mb-0.5">App version: {appVersion}</Text> : null}
          {dateRaw ? <Text className="text-[12px] text-muted">{formatValue("created_at", dateRaw)}</Text> : null}
        </Card>

        {message ? (
          <Card className="mb-3">
            <Text className="text-[13px] font-semibold text-muted mb-1.5 uppercase tracking-wide">Message</Text>
            <Text className="text-[16px] text-ink">{message}</Text>
          </Card>
        ) : null}

        {steps ? (
          <Card className="mb-3">
            <Text className="text-[13px] font-semibold text-muted mb-1.5 uppercase tracking-wide">Steps to reproduce</Text>
            <Text className="text-[16px] text-ink">{steps}</Text>
          </Card>
        ) : null}

        {Object.keys(rest).length > 0 ? <KeyValueList data={rest} title="Other details" /> : null}

        <Card className="mb-3">
          <Text className="text-[13px] font-semibold text-muted mb-1.5 uppercase tracking-wide">Reply to student</Text>
          <TextInput
            value={replyText}
            onChangeText={setReplyText}
            multiline
            maxLength={4000}
            placeholder="Type your reply — sending it resolves the ticket"
            placeholderTextColor="#8E8E93"
            className="bg-background border border-line rounded-2xl px-4 py-3 text-ink mb-2"
            style={{ minHeight: 90, textAlignVertical: "top" }}
          />
          <Button
            label="Send reply & resolve"
            variant="primary"
            disabled={!replyText.trim()}
            loading={replyMutation.isPending}
            onPress={() => replySheetRef.current?.present()}
          />
        </Card>

        {resolved ? (
          <Button
            label="Reopen ticket"
            variant="ghost"
            loading={reopenMutation.isPending}
            onPress={() => reopenSheetRef.current?.present()}
          />
        ) : null}
      </ScrollView>

      <ConfirmSheet
        ref={replySheetRef}
        title="Send this reply?"
        message="This resolves the ticket and messages the student."
        confirmLabel="Send"
        danger={false}
        onConfirm={() => {
          replySheetRef.current?.dismiss();
          replyMutation.mutate();
        }}
      />
      <ConfirmSheet
        ref={reopenSheetRef}
        title="Reopen this ticket?"
        confirmLabel="Reopen"
        danger={false}
        onConfirm={() => {
          reopenSheetRef.current?.dismiss();
          reopenMutation.mutate();
        }}
      />
    </KeyboardAvoidingView>
  );
}
