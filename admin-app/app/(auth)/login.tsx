import { zodResolver } from "@hookform/resolvers/zod";
import { MotiView } from "moti";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { API_URL, apiErrorMessage, checkBackendConnection } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<{ ok: boolean; detail: string } | null>(null);

  const runConnectionCheck = async () => {
    setChecking(true);
    setCheckResult(null);
    const result = await checkBackendConnection();
    setCheckResult(result);
    setChecking(false);
  };

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setServerError(null);
    try {
      await login(data.email.trim().toLowerCase(), data.password);
    } catch (err) {
      setServerError(apiErrorMessage(err, "Email kiva password chukicha"));
      setShakeKey((k) => k + 1);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} className="flex-1 bg-brand">
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled">
        <View className="h-[38%] items-center justify-end pb-8">
          <Text className="text-4xl font-extrabold text-brand-ink">Job Alert Admin</Text>
          <Text className="text-brand-ink/70 mt-1">Manage jobs, students & payments</Text>
        </View>

        <View className="flex-1 bg-background rounded-t-[28px] px-6 pt-8">
          <MotiView
            key={shakeKey}
            from={{ translateX: 0 }}
            animate={{ translateX: 0 }}
            transition={{ type: "timing", duration: 60 }}
          >
            <Text className="text-lg font-bold text-ink mb-6">Log in</Text>

            <Text className="text-sm font-semibold text-muted mb-1.5">Email</Text>
            <Controller
              control={control}
              name="email"
              render={({ field: { onChange, value, onBlur } }) => (
                <TextInput
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  placeholder="owner@example.com"
                  placeholderTextColor="#9AA39B"
                  autoCapitalize="none"
                  keyboardType="email-address"
                  className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-1"
                />
              )}
            />
            {errors.email ? <Text className="text-danger text-xs mb-2">{errors.email.message}</Text> : <View className="mb-3" />}

            <Text className="text-sm font-semibold text-muted mb-1.5 mt-2">Password</Text>
            <View className="flex-row items-center bg-surface border border-line rounded-2xl px-4 mb-1">
              <Controller
                control={control}
                name="password"
                render={({ field: { onChange, value, onBlur } }) => (
                  <TextInput
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    placeholder="••••••••"
                    placeholderTextColor="#9AA39B"
                    secureTextEntry={!showPassword}
                    className="flex-1 py-3.5 text-ink"
                  />
                )}
              />
              <Pressable onPress={() => setShowPassword((s) => !s)} hitSlop={10}>
                <Text className="text-info text-sm font-semibold">{showPassword ? "Hide" : "Show"}</Text>
              </Pressable>
            </View>
            {errors.password ? (
              <Text className="text-danger text-xs mb-2">{errors.password.message}</Text>
            ) : (
              <View className="mb-3" />
            )}

            {serverError ? <Text className="text-danger text-sm mb-3 text-center">{serverError}</Text> : null}

            <View className="mt-3">
              <Button label="Login" onPress={handleSubmit(onSubmit)} loading={loading} variant="primary" />
            </View>

            <View className="mt-6 items-center">
              <Pressable onPress={runConnectionCheck} hitSlop={10}>
                <Text className="text-xs text-muted underline">
                  {checking ? "Checking..." : "Server connection check kara"}
                </Text>
              </Pressable>
              <Text className="text-[10px] text-muted/70 mt-1 text-center">{API_URL}</Text>
              {checkResult ? (
                <Text
                  className={`text-xs mt-2 text-center ${checkResult.ok ? "text-go" : "text-danger"}`}
                >
                  {checkResult.ok ? "✓ Server reachable — " : "✗ Server la pochu shaklo nahi — "}
                  {checkResult.detail}
                </Text>
              ) : null}
            </View>
          </MotiView>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
