import { Tabs } from "expo-router";
import { MotiView } from "moti";
import { Text } from "react-native";

import { useIsOwner } from "@/store/auth";

function TabIcon({ emoji, focused }: { emoji: string; focused: boolean }) {
  return (
    <MotiView
      animate={{ scale: focused ? 1.15 : 1 }}
      transition={{ type: "timing", duration: 200 }}
    >
      <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.6 }}>{emoji}</Text>
    </MotiView>
  );
}

export default function TabsLayout() {
  const isOwner = useIsOwner();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#2A2000",
        tabBarInactiveTintColor: "#59615B",
        tabBarStyle: { borderTopColor: "#DDE1D8" },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
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
