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
import { COMMON_HIDDEN_KEYS, firstOfBool, firstOfString, type AnyRecord } from "@/lib/ghostlyFormat";
import { updateGhostlyUserPlan } from "@/lib/ghostlyApi";

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
  const [blocked, setBlocked] = useState(() => firstOfBool(user, ["blocked", "is_blocked"]) ?? false);

  const blockSheetRef = useRef<BottomSheetModal>(null);
  const planSheetRef = useRef<BottomSheetModal>(null);

  const name = firstOfString(user, ["name", "full_name", "username"], "Unnamed user");
  const email = firstOfString(user, ["email", "email_address"]);
  const shownKeys = ["name", "full_name", "username", "email", "email_address", ...COMMON_HIDDEN_KEYS];
  const rest = Object.fromEntries(Object.entries(user).filter(([k]) => !shownKeys.includes(k.toLowerCase())));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["ghostly-users"] });
    queryClient.invalidateQueries({ queryKey: ["ghostly-stats"] });
  };

  const blockMutation = useMutation({
    mutationFn: () => updateGhostlyUserPlan(id, { blocked: !blocked }),
    onSuccess: () => {
      setBlocked((b) => !b);
      invalidate();
      show(blocked ? "User unblocked" : "User blocked", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

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
              <Text className="text-sm font-semibold text-muted mb-1.5">Days</Text>
              <TextInput
                value={days}
                onChangeText={(t) => setDays(t.replace(/[^0-9]/g, ""))}
                keyboardType="number-pad"
                className="bg-background border border-line rounded-2xl px-4 py-3 text-ink"
              />
            </View>
          ) : null}
          <Button
            label={planChoice === "pro" ? `Make Pro for ${days || "30"} days` : "Move to Free"}
            variant="brand"
            onPress={() => planSheetRef.current?.present()}
            loading={planMutation.isPending}
          />
        </Card>

        <Card className="mb-3">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">Access</Text>
          <Button
            label={blocked ? "Unblock user" : "Block user"}
            variant={blocked ? "brand" : "danger"}
            onPress={() => blockSheetRef.current?.present()}
            loading={blockMutation.isPending}
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
        ref={blockSheetRef}
        title={blocked ? "Unblock this user?" : "Block this user?"}
        message={blocked ? "They will regain access to the app." : "They will lose access to the app immediately."}
        confirmLabel={blocked ? "Unblock" : "Block"}
        danger={!blocked}
        onConfirm={() => {
          blockSheetRef.current?.dismiss();
          blockMutation.mutate();
        }}
      />

      <ConfirmSheet
        ref={planSheetRef}
        title={planChoice === "pro" ? `Make Pro for ${days || "30"} days?` : "Move this user to Free?"}
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
