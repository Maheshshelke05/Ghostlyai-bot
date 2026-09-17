import "../global.css";

import { Baloo2_700Bold, Baloo2_800ExtraBold } from "@expo-google-fonts/baloo-2";
import { Mukta_400Regular, Mukta_600SemiBold } from "@expo-google-fonts/mukta";
import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect, useState } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AnimatedSplash } from "@/components/AnimatedSplash";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { GlobalAlerts } from "@/components/GlobalAlerts";
import { OfflineBanner } from "@/components/OfflineBanner";
import { ToastProvider } from "@/components/ui/Toast";
import { UpdateBanner } from "@/components/UpdateBanner";
import { WorkspaceSwitchOverlay } from "@/components/WorkspaceSwitchOverlay";
import { installCrashHandler } from "@/lib/crashHandler";
import { queryClient } from "@/lib/query-client";
import { useAppModeStore } from "@/store/appMode";
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
  const modeHydrated = useAppModeStore((s) => s.hydrated);
  const mode = useAppModeStore((s) => s.mode);
  const [splashDone, setSplashDone] = useState(false);

  const ready = fontsLoaded && hydrated && modeHydrated;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  if (!splashDone) {
    return (
      <GestureHandlerRootView style={{ flex: 1 }}>
        <AnimatedSplash onFinish={() => setSplashDone(true)} />
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ErrorBoundary>
          <QueryClientProvider client={queryClient}>
            <BottomSheetModalProvider>
              <ToastProvider>
                <OfflineBanner />
                {token ? <GlobalAlerts /> : null}
                {token ? <UpdateBanner /> : null}
                <WorkspaceSwitchOverlay />
                <Stack
                  screenOptions={{
                    headerShown: false,
                    // iOS navigation-bar look: white, no shadow line, bold 17pt title, tinted back button
                    headerStyle: { backgroundColor: "#FFFFFF" },
                    headerShadowVisible: false,
                    headerTintColor: "#EA580C",
                    headerTitleStyle: { fontWeight: "600", fontSize: 17, color: "#1C1C1E" },
                    headerBackButtonDisplayMode: "minimal",
                    contentStyle: { backgroundColor: "#F2F2F7" },
                  }}
                >
                  <Stack.Protected guard={!!token && mode === "jobalert"}>
                    <Stack.Screen name="(tabs)" />
                    <Stack.Screen name="jobs/new" options={{ presentation: "modal", headerShown: true, title: "Add job" }} />
                    <Stack.Screen name="jobs/[id]" options={{ headerShown: true, title: "Job" }} />
                    <Stack.Screen name="jobs/ai-review" options={{ headerShown: true, title: "Review AI drafts" }} />
                    <Stack.Screen name="users/[id]" options={{ headerShown: true, title: "User" }} />
                    <Stack.Screen name="categories/index" options={{ headerShown: true, title: "Categories" }} />
                    <Stack.Screen name="broadcast" options={{ presentation: "modal", headerShown: true, title: "Broadcast" }} />
                    <Stack.Screen name="settings" options={{ headerShown: true, title: "Settings" }} />
                    <Stack.Screen name="staff" options={{ headerShown: true, title: "Staff accounts" }} />
                    <Stack.Screen name="support/index" options={{ headerShown: true, title: "Support inbox" }} />
                    <Stack.Screen name="support/[userId]" options={{ headerShown: true, title: "Conversation" }} />
                    <Stack.Screen name="delivery" options={{ headerShown: true, title: "Delivery report" }} />
                  </Stack.Protected>
                  <Stack.Protected guard={!!token && mode === "ghostly"}>
                    <Stack.Screen name="(ghostly)" />
                    <Stack.Screen name="ghostly-user/[id]" options={{ headerShown: true, title: "User" }} />
                    <Stack.Screen name="ghostly-ticket/[id]" options={{ headerShown: true, title: "Ticket" }} />
                    <Stack.Screen name="ghostly-compose-email" options={{ presentation: "modal", headerShown: true, title: "New email" }} />
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
