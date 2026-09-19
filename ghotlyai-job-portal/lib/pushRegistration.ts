/** OS-level push notifications for students: new matching jobs / support replies, delivered
 * even while the app is fully closed. Requires a Firebase project wired up for Android
 * (google-services.json) - until that's in place, permission requests still work but
 * `getExpoPushTokenAsync` fails, which this treats as "no token" rather than a crash.
 *
 * `expo-notifications` is loaded via `require()` inside a try/catch rather than a static
 * `import` - Metro hoists ES imports above everything else in the module, including a
 * try/catch, and the module itself throws synchronously on evaluation in Expo Go on Android
 * (SDK 53+ dropped remote push support there), which would otherwise crash the whole app on
 * startup. A real dev/production build (where push actually works) is unaffected.
 */
import Constants from "expo-constants";
import { Platform } from "react-native";

type NotificationsModule = typeof import("expo-notifications");

let Notifications: NotificationsModule | null = null;
try {
  Notifications = require("expo-notifications");
  Notifications?.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
} catch (err) {
  console.warn("Push notifications unavailable in this runtime", err);
  Notifications = null;
}

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  if (!Notifications) return null;
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "GhotlyAI Job Portal",
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
