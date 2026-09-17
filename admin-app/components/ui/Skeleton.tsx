import { MotiView } from "moti";
import { View } from "react-native";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <MotiView
      className={`bg-line/70 rounded-lg ${className}`}
      from={{ opacity: 0.4 }}
      animate={{ opacity: 1 }}
      transition={{ type: "timing", duration: 700, loop: true }}
    />
  );
}

export function CardSkeleton() {
  return (
    <View className="rounded-2xl bg-surface p-4 mb-2 mx-4">
      <Skeleton className="h-4 w-1/2 mb-3" />
      <Skeleton className="h-3 w-3/4 mb-2" />
      <Skeleton className="h-3 w-2/3" />
    </View>
  );
}

export function ListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <View>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </View>
  );
}
