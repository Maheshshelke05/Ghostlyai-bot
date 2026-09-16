import "../global.css";

import { Baloo2_700Bold, Baloo2_800ExtraBold } from "@expo-google-fonts/baloo-2";
import { Mukta_400Regular, Mukta_600SemiBold } from "@expo-google-fonts/mukta";
import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OfflineBanner } from "@/components/OfflineBanner";
import { ToastProvider } from "@/components/ui/Toast";
import { installCrashHandler } from "@/lib/crashHandler";
import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/store/auth";

SplashScreen.preventAutoHideAsync().catch(() => {});
installCrashHandler();

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Baloo2_700Bold,
    Baloo2_800ExtraBold,
    Mukta_400Regular,
    Mukta_600SemiBold,
  });
  const hydrated = useAuthStore((s) => s.hydrated);
  const token = useAuthStore((s) => s.token);

  const ready = fontsLoaded && hydrated;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ErrorBoundary>
          <QueryClientProvider client={queryClient}>
            <BottomSheetModalProvider>
              <ToastProvider>
                <OfflineBanner />
                <Stack screenOptions={{ headerShown: false }}>
                  <Stack.Protected guard={!!token}>
                    <Stack.Screen name="(tabs)" />
                    <Stack.Screen name="jobs/new" options={{ presentation: "modal", headerShown: true, title: "Add job" }} />
                    <Stack.Screen name="jobs/[id]" options={{ headerShown: true, title: "Job" }} />
                    <Stack.Screen name="jobs/ai-review" options={{ headerShown: true, title: "Review AI drafts" }} />
                    <Stack.Screen name="users/[id]" options={{ headerShown: true, title: "User" }} />
                    <Stack.Screen name="categories/index" options={{ headerShown: true, title: "Categories" }} />
                    <Stack.Screen name="broadcast" options={{ presentation: "modal", headerShown: true, title: "Broadcast" }} />
                    <Stack.Screen name="settings" options={{ headerShown: true, title: "Settings" }} />
                    <Stack.Screen name="staff" options={{ headerShown: true, title: "Staff accounts" }} />
                  </Stack.Protected>
                  <Stack.Protected guard={!token}>
                    <Stack.Screen name="(auth)" />
                  </Stack.Protected>
                </Stack>
              </ToastProvider>
            </BottomSheetModalProvider>
          </QueryClientProvider>
        </ErrorBoundary>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
