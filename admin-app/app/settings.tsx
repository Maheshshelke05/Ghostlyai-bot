import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, getSettings, updateSettings, type SettingsData } from "@/lib/api";
import { useAppModeStore } from "@/store/appMode";

type NumericKey =
  | "price_inr"
  | "subscription_days"
  | "trial_days"
  | "digest_max_jobs"
  | "max_categories"
  | "teaser_every_hours"
  | "job_delay_minutes";

const NUMBER_FIELDS: { key: NumericKey; label: string }[] = [
  { key: "price_inr", label: "Price (₹)" },
  { key: "subscription_days", label: "Subscription length (days)" },
  { key: "trial_days", label: "Free trial (days)" },
  { key: "digest_max_jobs", label: "Jobs per digest" },
  { key: "max_categories", label: "Max categories per student" },
  { key: "teaser_every_hours", label: "Teaser every (hours)" },
  { key: "job_delay_minutes", label: "Hold new jobs before sending (minutes)" },
];

export default function SettingsScreen() {
  const { show } = useToast();
  const queryClient = useQueryClient();
  const beginSwitch = useAppModeStore((s) => s.beginSwitch);
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const [form, setForm] = useState<SettingsData | null>(null);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (payload: Partial<SettingsData>) => updateSettings(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings"], updated);
      show("Settings saved", "success");
    },
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  if (isLoading || !form) {
    return (
      <View className="flex-1 bg-background pt-4">
        <ListSkeleton />
      </View>
    );
  }

  const set = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const validationError = (f: SettingsData): string | null => {
    const empty = NUMBER_FIELDS.find(({ key }) => Number.isNaN(f[key]));
    if (empty) return `Enter a value for "${empty.label}"`;
    if (f.price_inr <= 0) return "Price must be greater than 0";
    if (f.subscription_days <= 0) return "Subscription length must be greater than 0";
    if (f.trial_days < 0) return "Free trial days cannot be negative";
    if (f.digest_max_jobs <= 0 || f.digest_max_jobs > 50) return "Jobs per digest must be between 1 and 50";
    if (f.max_categories <= 0 || f.max_categories > 10) return "Max categories must be between 1 and 10";
    if (f.teaser_every_hours <= 0) return "Teaser hours must be greater than 0";
    if (f.job_delay_minutes < 0 || f.job_delay_minutes > 1440) return "Hold time must be between 0 and 1440 minutes";
    return null;
  };

  const save = () => {
    const error = validationError(form);
    if (error) {
      show(error, "warn");
      return;
    }
    saveMutation.mutate(form);
  };

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 120 }}>
        <Card className="mb-4">
          <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">Workspace</Text>
          <Text className="text-[14px] text-muted mb-3">
            Switch this app to show GhostlyAI.in's admin data instead — users, support tickets,
            email stats and announcements for that product. Come back here anytime to switch back.
          </Text>
          <Button label="👻 Switch to GhotlyAI.in" variant="brand" onPress={() => beginSwitch("ghostly")} />
        </Card>

        {NUMBER_FIELDS.map(({ key, label }) => (
          <NumberField key={key} label={label} value={form[key]} onChange={(v) => set(key, v)} />
        ))}
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-background border-t border-line px-4 pt-3 pb-6">
        <Button label="Save" onPress={save} loading={saveMutation.isPending} />
      </View>
    </View>
  );
}

// An empty box is held as NaN rather than coerced to 0, so clearing the field to type a new
// number doesn't instantly snap back to "0"; save() refuses to submit while one is empty.
function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <View className="mb-3">
      <Text className="text-sm font-semibold text-muted mb-1.5">{label}</Text>
      <TextInput
        value={Number.isNaN(value) ? "" : String(value)}
        onChangeText={(text) => {
          const digits = text.replace(/[^0-9]/g, "");
          onChange(digits === "" ? Number.NaN : parseInt(digits, 10));
        }}
        keyboardType="number-pad"
        placeholder="Enter a number"
        placeholderTextColor="#9AA39B"
        className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink"
      />
    </View>
  );
}
