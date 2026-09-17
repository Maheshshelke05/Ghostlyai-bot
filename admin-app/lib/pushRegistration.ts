/** OS-level push notifications for admins: new signup / new support message on either
 * workspace, delivered even while the app is fully closed (unlike GlobalAlerts' in-app toasts,
 * which only fire while the app is open). Requires a Firebase project wired up for Android
 * (google-services.json) - until that's in place, permission requests still work but
 * `getExpoPushTokenAsync` fails, which this treats as "no token" rather than a crash.
 */
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Job Alert Admin",
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#EA580C",
      });
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== "granted") return null;

    const projectId = (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId;
    if (!projectId) return null;

    const { data } = await Notifications.getExpoPushTokenAsync({ projectId });
    return data;
  } catch (err) {
    // Most likely cause right now: no google-services.json wired up yet for this Android
    // build. Not fatal - the app just won't have a push token until that's in place.
    console.warn("Push registration failed", err);
    return null;
  }
}
