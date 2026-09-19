import { Link, Stack } from "expo-router";
import { Text, View } from "react-native";

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: "Not found" }} />
      <View className="flex-1 items-center justify-center bg-background px-6">
        <Text className="text-5xl mb-3">🔍</Text>
        <Text className="font-body text-muted text-center mb-4">This page doesn't exist.</Text>
        <Link href="/" className="text-brand font-body-strong">
          Go back home
        </Link>
      </View>
    </>
  );
}
