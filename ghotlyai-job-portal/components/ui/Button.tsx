import * as Haptics from "expo-haptics";
import { MotiView } from "moti";
import { useState } from "react";
import { ActivityIndicator, Pressable, Text, type GestureResponderEvent } from "react-native";

// iOS button styles: "primary" is the filled tint button, "brand" the tinted (translucent)
// one, "ghost" the plain bordered one, "danger" the tinted destructive one.
type Variant = "primary" | "brand" | "ghost" | "danger";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-brand",
  brand: "bg-brand-soft",
  ghost: "bg-surface border border-line",
  danger: "bg-danger/10",
};

const VARIANT_TEXT_CLASSES: Record<Variant, string> = {
  primary: "text-white",
  brand: "text-brand",
  ghost: "text-brand",
  danger: "text-danger",
};

const SPINNER_COLOR: Record<Variant, string> = {
  primary: "#FFFFFF",
  brand: "#16A34A",
  ghost: "#16A34A",
  danger: "#FF3B30",
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
    <MotiView
      animate={{ scale: pressed ? 0.96 : 1, opacity: pressed ? 0.85 : 1 }}
      transition={{ type: "spring", damping: 18, stiffness: 320 }}
    >
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
        className={`flex-row items-center justify-center rounded-[14px] px-5 ${
          fullWidth ? "w-full" : ""
        } ${VARIANT_CLASSES[variant]} ${isDisabled ? "opacity-40" : ""}`}
        style={{ minHeight: 50 }}
      >
        {loading ? (
          <ActivityIndicator color={SPINNER_COLOR[variant]} />
        ) : (
          <>
            {icon}
            <Text className={`text-[17px] font-semibold ${VARIANT_TEXT_CLASSES[variant]} ${icon ? "ml-2" : ""}`}>
              {label}
            </Text>
          </>
        )}
      </Pressable>
    </MotiView>
  );
}
