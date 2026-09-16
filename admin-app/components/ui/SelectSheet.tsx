import { BottomSheetBackdrop, BottomSheetFlatList, BottomSheetModal, BottomSheetTextInput } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";

export interface SelectOption {
  label: string;
  value: string;
}

interface SelectSheetProps {
  title: string;
  options: SelectOption[];
  onSelect: (value: string) => void;
  searchable?: boolean;
}

export const SelectSheet = forwardRef<BottomSheetModal, SelectSheetProps>(function SelectSheet(
  { title, options, onSelect, searchable = true },
  ref
) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) return options;
    const q = query.trim().toLowerCase();
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, query]);

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={["70%"]}
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: "#FFFFFF", borderRadius: 24 }}
    >
      <View className="px-4 pb-2">
        <Text className="text-lg font-bold text-ink mb-2">{title}</Text>
        {searchable ? (
          <BottomSheetTextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search..."
            className="bg-background rounded-xl px-4 py-3 text-ink"
          />
        ) : null}
      </View>
      <BottomSheetFlatList
        data={filtered}
        keyExtractor={(item) => item.value}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => onSelect(item.value)}
            className="px-4 py-3.5 border-b border-line/50 active:bg-background"
          >
            <Text className="text-base text-ink">{item.label}</Text>
          </Pressable>
        )}
        contentContainerStyle={{ paddingBottom: 24 }}
      />
    </BottomSheetModal>
  );
});
