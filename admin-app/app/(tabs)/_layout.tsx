import * as Haptics from "expo-haptics";
import { Tabs } from "expo-router";
import { MotiView } from "moti";
import type { ComponentProps, ReactNode } from "react";
import { Platform, Pressable, Text, View } from "react-native";

import { useIsOwner } from "@/store/auth";

type TabButtonProps = Omit<ComponentProps<typeof Pressable>, "children"> & { children?: ReactNode };

function HapticTabButton({ onPress, children, ...rest }: TabButtonProps) {
  return (
    <Pressable
      {...rest}
      onPress={(e) => {
        Haptics.selectionAsync().catch(() => {});
        onPress?.(e);
      }}
    >
      {children}
    </Pressable>
  );
}

// iOS tab bar: white, hairline on top, tint colour for the active tab, and a soft pill
// that springs in behind the active icon.
function TabIcon({ emoji, focused }: { emoji: string; focused: boolean }) {
  return (
    <View style={{ alignItems: "center", justifyContent: "center", width: 56, height: 32 }}>
      <MotiView
        animate={{ opacity: focused ? 1 : 0, scaleX: focused ? 1 : 0.6 }}
        transition={{ type: "spring", damping: 14, stiffness: 220 }}
        style={{
          position: "absolute",
          width: 56,
          height: 32,
          borderRadius: 16,
          backgroundColor: "#FFF1E8",
        }}
      />
      <MotiView
        animate={{ scale: focused ? 1.12 : 1, translateY: focused ? -1 : 0 }}
        transition={{ type: "spring", damping: 10, stiffness: 260 }}
      >
        <Text style={{ fontSize: 21, opacity: focused ? 1 : 0.55 }}>{emoji}</Text>
      </MotiView>
    </View>
  );
}

export default function TabsLayout() {
  const isOwner = useIsOwner();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#EA580C",
        tabBarInactiveTintColor: "#8E8E93",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#E5E5EA",
          borderTopWidth: 0.5,
          height: Platform.OS === "ios" ? 84 : 66,
          paddingTop: 6,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600", marginTop: 2 },
        tabBarButton: (props) => <HapticTabButton {...(props as unknown as TabButtonProps)} />,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          href: isOwner ? undefined : null,
          title: "Dashboard",
          tabBarIcon: ({ focused }) => <TabIcon emoji="🏠" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="jobs/index"
        options={{
          title: "Jobs",
          tabBarIcon: ({ focused }) => <TabIcon emoji="💼" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="users/index"
        options={{
          href: isOwner ? undefined : null,
          title: "Users",
          tabBarIcon: ({ focused }) => <TabIcon emoji="👥" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="payments/index"
        options={{
          href: isOwner ? undefined : null,
          title: "Payments",
          tabBarIcon: ({ focused }) => <TabIcon emoji="💳" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="more/index"
        options={{
          title: "More",
          tabBarIcon: ({ focused }) => <TabIcon emoji="⋯" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
