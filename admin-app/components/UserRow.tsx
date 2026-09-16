import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { AccessBadge } from "@/components/ui/Badge";
import type { UserRow as UserRowType } from "@/lib/api";

function initials(name: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function UserRow({ user }: { user: UserRowType }) {
  return (
    <Pressable
      onPress={() => router.push(`/users/${user.id}`)}
      className="flex-row items-center bg-surface border border-line/60 rounded-[18px] p-3.5 mb-3 mx-4"
    >
      <View className="w-11 h-11 rounded-full bg-brand items-center justify-center mr-3">
        <Text className="text-brand-ink font-bold">{initials(user.full_name)}</Text>
      </View>
      <View className="flex-1">
        <Text className="text-base font-semibold text-ink" numberOfLines={1}>
          {user.full_name || "Unnamed"}
        </Text>
        <Text className="text-xs text-muted mt-0.5" numberOfLines={1}>
          {user.district || "Kuthehi"} • {user.categories.join(", ") || "No categories"}
        </Text>
      </View>
      <AccessBadge access={user.access} />
    </Pressable>
  );
}
