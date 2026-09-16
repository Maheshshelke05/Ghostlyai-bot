import NetInfo from "@react-native-community/netinfo";
import { AnimatePresence, MotiView } from "moti";
import { useEffect, useState } from "react";
import { Text } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export function OfflineBanner() {
  const [offline, setOffline] = useState(false);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      setOffline(state.isConnected === false || state.isInternetReachable === false);
    });
    return () => unsubscribe();
  }, []);

  return (
    <AnimatePresence>
      {offline ? (
        <MotiView
          from={{ translateY: -40, opacity: 0 }}
          animate={{ translateY: 0, opacity: 1 }}
          exit={{ translateY: -40, opacity: 0 }}
          transition={{ type: "timing", duration: 200 }}
          className="absolute left-0 right-0 bg-danger items-center py-2"
          style={{ top: insets.top, zIndex: 200 }}
        >
          <Text className="text-white text-xs font-semibold">
            📡 Internet nahi. Kahi features kaam karnar nahit.
          </Text>
        </MotiView>
      ) : null}
    </AnimatePresence>
  );
}
