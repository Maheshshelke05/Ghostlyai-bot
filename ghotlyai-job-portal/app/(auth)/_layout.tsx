import { Stack } from "expo-router";

export default function AuthLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="welcome" />
      <Stack.Screen name="login" />
      <Stack.Screen name="splash" />
      <Stack.Screen name="name" />
      <Stack.Screen name="resume" />
      <Stack.Screen name="creating-profile" />
      <Stack.Screen name="set-password" />
    </Stack>
  );
}
