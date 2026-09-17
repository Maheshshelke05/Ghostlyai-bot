import { Pressable, Text, TextInput, View } from "react-native";

/** iOS search field: grey capsule, magnifier, clear button while there's text. */
export function SearchBar({
  value,
  onChangeText,
  placeholder = "Search",
}: {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
}) {
  return (
    <View className="flex-row items-center bg-line/70 rounded-xl px-3 mb-3" style={{ height: 40 }}>
      <Text className="text-muted mr-2">🔍</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#8E8E93"
        className="flex-1 text-[16px] text-ink"
        autoCorrect={false}
        autoCapitalize="none"
        clearButtonMode="while-editing"
        returnKeyType="search"
      />
      {value ? (
        <Pressable onPress={() => onChangeText("")} hitSlop={8} className="w-5 h-5 rounded-full bg-muted items-center justify-center ml-1">
          <Text className="text-white text-[11px] font-bold" style={{ marginTop: -1 }}>✕</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
