import { Stack } from "expo-router";

export default function OnboardingLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="job-types" />
      <Stack.Screen name="categories" />
    </Stack>
  );
}
