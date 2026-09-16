import { View, type ViewProps } from "react-native";

export function Card({ className = "", ...rest }: ViewProps & { className?: string }) {
  return (
    <View
      className={`rounded-[18px] bg-surface p-4 border border-line/60 dark:border-line/20 ${className}`}
      {...rest}
    />
  );
}
