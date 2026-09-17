import { useEffect, useRef } from "react";

import { setPushToken } from "@/lib/api";
import { registerForPushNotificationsAsync } from "@/lib/pushRegistration";
import { useAuthStore } from "@/store/auth";

/** Registers this device for push notifications once per login, silently - no toggle to
 * build/maintain, and re-registering the same token on every app open is harmless (the
 * backend just overwrites the same value). If the OS permission prompt is denied, or Android
 * push isn't wired up yet (no Firebase project configured), this just does nothing rather
 * than erroring - see lib/pushRegistration.ts. */
export function PushRegistration() {
  const token = useAuthStore((s) => s.token);
  const registeredFor = useRef<string | null>(null);

  useEffect(() => {
    if (!token || registeredFor.current === token) return;
    registeredFor.current = token;

    registerForPushNotificationsAsync().then((expoPushToken) => {
      if (expoPushToken) {
        setPushToken(expoPushToken).catch(() => {
          // Non-fatal: worst case, this admin just doesn't get push notifications this session.
        });
      }
    });
  }, [token]);

  return null;
}
