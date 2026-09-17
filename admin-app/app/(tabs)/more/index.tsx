import { BottomSheetBackdrop, BottomSheetModal, BottomSheetTextInput, BottomSheetView } from "@gorhom/bottom-sheet";
import Constants from "expo-constants";
import { router } from "expo-router";
import { forwardRef, useCallback, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, changePassword } from "@/lib/api";
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

  return (
    <View className="flex-1 bg-background" style={{ paddingTop: insets.top + 16 }}>
      <View className="px-4 mb-4">
        <Text className="text-2xl font-extrabold text-ink">More</Text>
        <Text className="text-sm text-muted mt-1">
          {admin?.name} • {admin?.email} • {admin?.role}
        </Text>
      </View>

      <View className="px-4 gap-3">
        {isOwner ? (
          <MenuRow label="🗂 Categories" onPress={() => router.push("/categories")} />
        ) : (
          <MenuRow label="🗂 Categories (view)" onPress={() => router.push("/categories")} />
        )}
        {isOwner ? <MenuRow label="⚙️ Settings" onPress={() => router.push("/settings")} /> : null}
        {isOwner ? <MenuRow label="🧑‍💻 Staff accounts" onPress={() => router.push("/staff")} /> : null}
        {isOwner ? <MenuRow label="📣 Broadcast" onPress={() => router.push("/broadcast")} /> : null}
        <MenuRow label="🔑 Change password" onPress={() => sheetRef.current?.present()} />
      </View>

      <View className="px-4 mt-6">
        <Button label="Logout" variant="danger" onPress={logout} />
      </View>

      <Text className="text-center text-xs text-muted mt-6">
        App version {Constants.expoConfig?.version ?? "1.0.0"}
      </Text>

      <ChangePasswordSheet ref={sheetRef} renderBackdrop={renderBackdrop} />
    </View>
  );
}

function MenuRow({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} className="bg-surface border border-line/60 rounded-2xl px-4 py-4">
      <Text className="text-base font-medium text-ink">{label}</Text>
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
