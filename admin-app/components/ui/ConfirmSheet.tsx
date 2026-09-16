import { BottomSheetBackdrop, BottomSheetModal, BottomSheetView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback } from "react";
import { Text, View } from "react-native";

import { Button } from "./Button";

interface ConfirmSheetProps {
  title: string;
  message?: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
}

export const ConfirmSheet = forwardRef<BottomSheetModal, ConfirmSheetProps>(function ConfirmSheet(
  { title, message, confirmLabel = "Confirm", danger = true, onConfirm },
  ref
) {
  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={["30%"]}
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: "#FFFFFF", borderRadius: 24 }}
    >
      <BottomSheetView className="px-5 pb-6 pt-2">
        <Text className="text-lg font-bold text-ink mb-1">{title}</Text>
        {message ? <Text className="text-sm text-muted mb-4">{message}</Text> : <View className="mb-4" />}
        <Button label={confirmLabel} variant={danger ? "danger" : "primary"} onPress={onConfirm} />
      </BottomSheetView>
    </BottomSheetModal>
  );
});
