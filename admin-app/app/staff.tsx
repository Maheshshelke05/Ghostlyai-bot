import { BottomSheetBackdrop, BottomSheetModal, BottomSheetTextInput, BottomSheetView } from "@gorhom/bottom-sheet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { forwardRef, useCallback, useRef, useState } from "react";
import { FlatList, Switch, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, createStaff, listStaff, updateStaff, type StaffRow } from "@/lib/api";

export default function StaffScreen() {
  const { show } = useToast();
  const queryClient = useQueryClient();
  const sheetRef = useRef<BottomSheetModal>(null);

  const { data, isLoading } = useQuery({ queryKey: ["staff"], queryFn: listStaff });

  const toggleMutation = useMutation({
    mutationFn: (staff: StaffRow) => updateStaff(staff.id, { is_active: !staff.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff"] }),
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  if (isLoading) {
    return (
      <View className="flex-1 bg-background pt-4">
        <ListSkeleton />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-background">
      <FlatList
        data={data ?? []}
        keyExtractor={(s) => String(s.id)}
        contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
        renderItem={({ item }) => (
          <View className="bg-surface border border-line/60 rounded-2xl p-4 mb-3 flex-row items-center justify-between">
            <View className="flex-1 pr-2">
              <Text className="text-base font-semibold text-ink">{item.name}</Text>
              <Text className="text-xs text-muted mt-0.5">
                {item.email} • {item.role}
              </Text>
            </View>
            <Switch value={item.is_active} onValueChange={() => toggleMutation.mutate(item)} />
          </View>
        )}
      />

      <View className="absolute bottom-6 left-4 right-4">
        <Button label="+ Staff" variant="brand" onPress={() => sheetRef.current?.present()} />
      </View>

      <NewStaffSheet ref={sheetRef} renderBackdrop={renderBackdrop} />
    </View>
  );
}

const NewStaffSheet = forwardRef<BottomSheetModal, { renderBackdrop: (props: any) => React.ReactElement }>(
  function NewStaffSheet({ renderBackdrop }, ref) {
    const { show } = useToast();
    const queryClient = useQueryClient();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async () => {
      if (!name.trim() || !email.trim() || password.length < 8) {
        show("Naav, email aani 8+ akshari password bhara", "warn");
        return;
      }
      setLoading(true);
      try {
        await createStaff({ name: name.trim(), email: email.trim().toLowerCase(), password, role: "uploader" });
        queryClient.invalidateQueries({ queryKey: ["staff"] });
        show("Staff account tayar", "success");
        setName("");
        setEmail("");
        setPassword("");
        (ref as React.RefObject<BottomSheetModal>).current?.dismiss();
      } catch (err) {
        show(apiErrorMessage(err), "error");
      } finally {
        setLoading(false);
      }
    };

    return (
      <BottomSheetModal ref={ref} snapPoints={["55%"]} backdropComponent={renderBackdrop}>
        <BottomSheetView className="px-5 pb-8 pt-2">
          <Text className="text-lg font-bold text-ink mb-4">New staff account</Text>
          <BottomSheetTextInput value={name} onChangeText={setName} placeholder="Name" className="bg-background rounded-xl px-4 py-3 text-ink mb-3" />
          <BottomSheetTextInput
            value={email}
            onChangeText={setEmail}
            placeholder="Email"
            autoCapitalize="none"
            keyboardType="email-address"
            className="bg-background rounded-xl px-4 py-3 text-ink mb-3"
          />
          <BottomSheetTextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Temporary password (8+ chars)"
            secureTextEntry
            className="bg-background rounded-xl px-4 py-3 text-ink mb-4"
          />
          <Button label="Create" onPress={submit} loading={loading} />
        </BottomSheetView>
      </BottomSheetModal>
    );
  }
);
