import * as Haptics from "expo-haptics";
import { MotiView } from "moti";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, type GestureResponderEvent } from "react-native";

type Variant = "primary" | "brand" | "ghost" | "danger";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-go",
  brand: "bg-brand",
  ghost: "bg-transparent border border-line",
  danger: "bg-danger",
};

const VARIANT_TEXT_CLASSES: Record<Variant, string> = {
  primary: "text-white",
  brand: "text-brand-ink",
  ghost: "text-ink dark:text-white",
  danger: "text-white",
};

interface ButtonProps {
  label: string;
  onPress?: (e: GestureResponderEvent) => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  label,
  onPress,
  variant = "primary",
  loading = false,
  disabled = false,
  fullWidth = true,
  icon,
}: ButtonProps) {
  const [pressed, setPressed] = useState(false);
  const isDisabled = disabled || loading;

  return (
    <MotiView animate={{ scale: pressed ? 0.97 : 1 }} transition={{ type: "timing", duration: 120 }}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: isDisabled }}
        disabled={isDisabled}
        onPressIn={() => setPressed(true)}
        onPressOut={() => setPressed(false)}
        onPress={(e) => {
          if (isDisabled) return;
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
          onPress?.(e);
        }}
        className={`flex-row items-center justify-center rounded-2xl px-5 py-3.5 ${
          fullWidth ? "w-full" : ""
        } ${VARIANT_CLASSES[variant]} ${isDisabled ? "opacity-50" : ""}`}
        style={{ minHeight: 48 }}
      >
        {loading ? (
          <ActivityIndicator color={variant === "brand" ? "#2A2000" : "#FFFFFF"} />
        ) : (
          <>
            {icon}
            <Text className={`text-base font-semibold ${VARIANT_TEXT_CLASSES[variant]} ${icon ? "ml-2" : ""}`}>
              {label}
            </Text>
          </>
        )}
      </Pressable>
    </MotiView>
  );
}
