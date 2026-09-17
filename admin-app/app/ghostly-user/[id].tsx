import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { ConfirmSheet } from "@/components/ui/ConfirmSheet";
import { KeyValueList } from "@/components/ui/KeyValueList";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api";
import { COMMON_HIDDEN_KEYS, firstOfString, isBlockedUser, type AnyRecord } from "@/lib/ghostlyFormat";
import { updateGhostlyUserPlan } from "@/lib/ghostlyApi";

// Block/unblock is deliberately NOT wired up here: live-tested against the real API and the
// endpoint returns {"success": true} without actually changing the user's status either way -
// the field name this write endpoint expects for blocking isn't "blocked" or "status" (both
// were tried). Shipping it would show a confident "User blocked" toast that lied. Plan change
// below IS confirmed working (verified live: plan flips and persists).

export default function GhostlyUserDetailScreen() {
  const { id, data } = useLocalSearchParams<{ id: string; data?: string }>();
  const queryClient = useQueryClient();
  const { show } = useToast();

  let user: AnyRecord = {};
  try {
    user = data ? JSON.parse(data) : {};
  } catch {
    user = {};
  }

  const [planChoice, setPlanChoice] = useState<"free" | "pro">(() => {
    const p = firstOfString(user, ["plan", "subscription_plan", "tier"], "free").toLowerCase();
    return p.includes("pro") ? "pro" : "free";
  });
  const [days, setDays] = useState("30");
  const blocked = isBlockedUser(user); // read-only badge below - see the note above on why

  const planSheetRef = useRef<BottomSheetModal>(null);

  const name = firstOfString(user, ["name", "full_name", "username"], "Unnamed user");
  const email = firstOfString(user, ["email", "email_address"]);
  const shownKeys = ["name", "full_name", "username", "email", "email_address", ...COMMON_HIDDEN_KEYS];
  const rest = Object.fromEntries(Object.entries(user).filter(([k]) => !shownKeys.includes(k.toLowerCase())));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["ghostly-users"] });
    queryClient.invalidateQueries({ queryKey: ["ghostly-stats"] });
  };

  const planMutation = useMutation({
    mutationFn: () => {
      const parsedDays = parseInt(days, 10);
      return updateGhostlyUserPlan(
        id,
        planChoice === "pro" ? { plan: "pro", days: Number.isFinite(parsedDays) && parsedDays > 0 ? parsedDays : 30 } : { plan: "free" }
      );
    },
    onSuccess: () => {
      invalidate();
      show("Plan updated", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card className="mb-3 items-center py-6">
          <View className="w-16 h-16 rounded-full bg-brand-soft items-center justify-center mb-2">
            <Text className="text-brand font-bold text-2xl">{name.trim().charAt(0).toUpperCase() || "?"}</Text>
          </View>
          <Text className="text-[20px] font-bold text-ink">{name}</Text>
          {email ? <Text className="text-[14px] text-muted mt-0.5">{email}</Text> : null}
          {blocked ? (
            <View className="bg-danger/10 rounded-full px-3 py-1 mt-2">
              <Text className="text-danger text-xs font-semibold">Blocked</Text>
            </View>
          ) : null}
        </Card>

        <Card className="mb-3">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">Change plan</Text>
          <View className="flex-row mb-2">
            <Chip label="Free" selected={planChoice === "free"} onPress={() => setPlanChoice("free")} />
            <Chip label="Pro" selected={planChoice === "pro"} onPress={() => setPlanChoice("pro")} />
          </View>
          {planChoice === "pro" ? (
            <View className="mb-2">
              <Text className="text-sm font-semibold text-muted mb-1.5">Days (sent to the API; not confirmed to limit the duration)</Text>
              <TextInput
                value={days}
                onChangeText={(t) => setDays(t.replace(/[^0-9]/g, ""))}
                keyboardType="number-pad"
                className="bg-background border border-line rounded-2xl px-4 py-3 text-ink"
              />
            </View>
          ) : null}
          <Button
            label={planChoice === "pro" ? "Make Pro" : "Move to Free"}
            variant="brand"
            onPress={() => planSheetRef.current?.present()}
            loading={planMutation.isPending}
          />
        </Card>

        {email ? (
          <Card className="mb-3">
            <Button
              label="Send email to this user"
              variant="ghost"
              onPress={() => router.push({ pathname: "/ghostly-compose-email", params: { to: email } })}
            />
          </Card>
        ) : null}

        {Object.keys(rest).length > 0 ? <KeyValueList data={rest} title="Full profile" /> : null}
      </ScrollView>

      <ConfirmSheet
        ref={planSheetRef}
        title={planChoice === "pro" ? "Make this user Pro?" : "Move this user to Free?"}
        message={name}
        confirmLabel="Confirm"
        danger={false}
        onConfirm={() => {
          planSheetRef.current?.dismiss();
          planMutation.mutate();
        }}
      />
    </View>
  );
}
