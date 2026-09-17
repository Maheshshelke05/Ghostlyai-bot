import { BottomSheetBackdrop, BottomSheetModal, BottomSheetTextInput, BottomSheetView } from "@gorhom/bottom-sheet";
import { useQuery } from "@tanstack/react-query";
import Constants from "expo-constants";
import { router } from "expo-router";
import { forwardRef, useCallback, useRef, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, changePassword, listSupportThreads } from "@/lib/api";
import { useAuthStore, useIsOwner } from "@/store/auth";

export default function MoreScreen() {
  const admin = useAuthStore((s) => s.admin);
  const logout = useAuthStore((s) => s.logout);
  const isOwner = useIsOwner();
  const insets = useSafeAreaInsets();
  const sheetRef = useRef<BottomSheetModal>(null);

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  const { data: openSupport } = useQuery({
    queryKey: ["support", "open", ""],
    queryFn: () => listSupportThreads({ status: "open", page: 1, size: 1 }),
    refetchInterval: 30_000,
  });
  const openCount = openSupport?.total ?? 0;

  return (
    <ScrollView className="flex-1 bg-background" contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: 40 }}>
      <ScreenHeader title="More" subtitle={`${admin?.name ?? ""} · ${admin?.role ?? ""}`} />

      <Section title="Students">
        <MenuRow icon="💬" label="Support inbox" badge={openCount} onPress={() => router.push("/support")} />
        {isOwner ? <MenuRow icon="📣" label="Broadcast" onPress={() => router.push("/broadcast")} /> : null}
        <MenuRow icon="📊" label="Delivery report" onPress={() => router.push("/delivery")} last />
      </Section>

      <Section title="Setup">
        <MenuRow icon="🗂" label={isOwner ? "Categories" : "Categories (view)"} onPress={() => router.push("/categories")} last={!isOwner} />
        {isOwner ? <MenuRow icon="⚙️" label="Settings" onPress={() => router.push("/settings")} /> : null}
        {isOwner ? <MenuRow icon="🧑‍💻" label="Staff accounts" onPress={() => router.push("/staff")} last /> : null}
      </Section>

      <Section title="Account">
        <MenuRow icon="🔑" label="Change password" onPress={() => sheetRef.current?.present()} />
        <MenuRow icon="🚪" label="Log out" destructive onPress={logout} last />
      </Section>

      <Text className="text-center text-xs text-muted mt-2">
        {admin?.email} · v{Constants.expoConfig?.version ?? "1.0.0"}
      </Text>

      <ChangePasswordSheet ref={sheetRef} renderBackdrop={renderBackdrop} />
    </ScrollView>
  );
}

// iOS inset-grouped list: a small caps header, then rows in one rounded white block
// separated by hairlines that start after the icon column.
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="px-4 mb-6">
      <Text className="text-[13px] text-muted uppercase tracking-wide mb-2 ml-1">{title}</Text>
      <View className="bg-surface rounded-2xl overflow-hidden">{children}</View>
    </View>
  );
}

function MenuRow({
  icon,
  label,
  badge,
  destructive,
  last,
  onPress,
}: {
  icon: string;
  label: string;
  badge?: number;
  destructive?: boolean;
  last?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} className="flex-row items-center pl-4 active:bg-background">
      <Text className="text-lg w-8">{icon}</Text>
      <View className={`flex-1 flex-row items-center justify-between py-3.5 pr-4 ${last ? "" : "border-b border-line"}`}>
        <Text className={`text-[17px] ${destructive ? "text-danger" : "text-ink"}`}>{label}</Text>
        <View className="flex-row items-center">
          {badge ? (
            <View className="bg-brand rounded-full min-w-[22px] h-[22px] px-1.5 items-center justify-center mr-2">
              <Text className="text-white text-xs font-bold">{badge > 99 ? "99+" : badge}</Text>
            </View>
          ) : null}
          {!destructive ? <Text className="text-line text-lg">›</Text> : null}
        </View>
      </View>
    </Pressable>
  );
}

const ChangePasswordSheet = forwardRef<BottomSheetModal, { renderBackdrop: (props: any) => React.ReactElement }>(
  function ChangePasswordSheet({ renderBackdrop }, ref) {
    const { show } = useToast();
    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async () => {
      if (newPassword.length < 8) {
        show("New password must be at least 8 characters", "warn");
        return;
      }
      setLoading(true);
      try {
        await changePassword(oldPassword, newPassword);
        show("Password changed", "success");
        setOldPassword("");
        setNewPassword("");
        (ref as React.RefObject<BottomSheetModal>).current?.dismiss();
      } catch (err) {
        show(apiErrorMessage(err, "Could not change password"), "error");
      } finally {
        setLoading(false);
      }
    };

    return (
      <BottomSheetModal ref={ref} snapPoints={["45%"]} backdropComponent={renderBackdrop}>
        <BottomSheetView className="px-5 pb-8 pt-2">
          <Text className="text-lg font-bold text-ink mb-4">Change password</Text>
          <BottomSheetTextInput
            value={oldPassword}
            onChangeText={setOldPassword}
            placeholder="Current password"
            secureTextEntry
            className="bg-background rounded-xl px-4 py-3 text-ink mb-3"
          />
          <BottomSheetTextInput
            value={newPassword}
            onChangeText={setNewPassword}
            placeholder="New password (8+ chars)"
            secureTextEntry
            className="bg-background rounded-xl px-4 py-3 text-ink mb-4"
          />
          <Button label="Update password" onPress={submit} loading={loading} />
        </BottomSheetView>
      </BottomSheetModal>
    );
  }
);
