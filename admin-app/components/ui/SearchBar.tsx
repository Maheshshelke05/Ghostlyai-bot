import { TextInput, View } from "react-native";

export function SearchBar({
  value,
  onChangeText,
  placeholder = "Search...",
}: {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
}) {
  return (
    <View className="flex-row items-center bg-surface border border-line rounded-2xl px-4 mb-3" style={{ height: 46 }}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#9AA39B"
        className="flex-1 text-ink dark:text-white"
        autoCorrect={false}
        autoCapitalize="none"
      />
    </View>
  );
}
