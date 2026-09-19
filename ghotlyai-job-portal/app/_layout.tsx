import "../global.css";

import { Hind_400Regular, Hind_600SemiBold } from "@expo-google-fonts/hind";
import { Poppins_600SemiBold, Poppins_700Bold } from "@expo-google-fonts/poppins";
import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { PushRegistration } from "@/components/PushRegistration";
import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/store/auth";

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Poppins_600SemiBold,
    Poppins_700Bold,
    Hind_400Regular,
    Hind_600SemiBold,
  });
  const hydrated = useAuthStore((s) => s.hydrated);
  const token = useAuthStore((s) => s.token);
  const nextStep = useAuthStore((s) => s.nextStep);

  const ready = fontsLoaded && hydrated;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  const onboarded = !!token && nextStep === "done";
  const needsOnboarding = !!token && nextStep !== "done";

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <BottomSheetModalProvider>
            {onboarded ? <PushRegistration /> : null}
            <Stack
              screenOptions={{
                headerShown: false,
                headerStyle: { backgroundColor: "#FFFFFF" },
                headerShadowVisible: false,
                headerTintColor: "#EA580C",
                headerTitleStyle: { fontWeight: "600", fontSize: 17, color: "#1C1C1E" },
                headerBackButtonDisplayMode: "minimal",
                contentStyle: { backgroundColor: "#FFFFFF" },
              }}
            >
              <Stack.Protected guard={onboarded}>
                <Stack.Screen name="(tabs)" />
                <Stack.Screen name="job/[id]" options={{ headerShown: true, title: "Job details" }} />
                <Stack.Screen name="filters" options={{ presentation: "modal", headerShown: true, title: "Filters" }} />
                <Stack.Screen name="payment/checkout" options={{ headerShown: true, title: "Subscribe" }} />
              </Stack.Protected>
              <Stack.Protected guard={needsOnboarding}>
                <Stack.Screen name="(onboarding)" />
              </Stack.Protected>
              <Stack.Protected guard={!token}>
                <Stack.Screen name="(auth)" />
              </Stack.Protected>
            </Stack>
          </BottomSheetModalProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
