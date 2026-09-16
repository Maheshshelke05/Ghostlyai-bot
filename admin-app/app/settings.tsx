import DateTimePicker from "@react-native-community/datetimepicker";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, getSettings, updateSettings, type SettingsData } from "@/lib/api";

export default function SettingsScreen() {
  const { show } = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const [form, setForm] = useState<SettingsData | null>(null);
  const [showTimePicker, setShowTimePicker] = useState(false);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (payload: Partial<SettingsData>) => updateSettings(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings"], updated);
      show("Settings save zale", "success");
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
    if (f.price_inr <= 0) return "Price 0 pekshaa jaast asava";
    if (f.subscription_days <= 0) return "Subscription divas 0 pekshaa jaast asave";
    if (f.trial_days < 0) return "Trial divas negative nasave";
    if (f.digest_max_jobs <= 0 || f.digest_max_jobs > 50) return "Jobs per digest 1-50 madhe asave";
    if (f.max_categories <= 0 || f.max_categories > 10) return "Max categories 1-10 madhe asave";
    if (f.teaser_every_hours <= 0) return "Teaser hours 0 pekshaa jaast asave";
    if (f.digest_times.length === 0) return "Kimaan ek digest time add kara";
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

  const addTime = (date: Date) => {
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    const value = `${hh}:${mm}`;
    if (!form.digest_times.includes(value)) {
      set("digest_times", [...form.digest_times, value].sort());
    }
  };

  return (
    <View className="flex-1 bg-background">
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 120 }}>
        <NumberField label="Price (₹)" value={form.price_inr} onChange={(v) => set("price_inr", v)} />
        <NumberField
          label="Subscription divas"
          value={form.subscription_days}
          onChange={(v) => set("subscription_days", v)}
        />
        <NumberField label="Trial divas" value={form.trial_days} onChange={(v) => set("trial_days", v)} />
        <NumberField
          label="Jobs per digest"
          value={form.digest_max_jobs}
          onChange={(v) => set("digest_max_jobs", v)}
        />
        <NumberField
          label="Max categories per student"
          value={form.max_categories}
          onChange={(v) => set("max_categories", v)}
        />
        <NumberField
          label="Teaser every (hours)"
          value={form.teaser_every_hours}
          onChange={(v) => set("teaser_every_hours", v)}
        />

        <Text className="text-sm font-semibold text-muted mb-1.5 mt-3">Digest times (IST)</Text>
        <View className="flex-row flex-wrap items-center mb-2">
          {form.digest_times.map((time) => (
            <Pressable
              key={time}
              onPress={() =>
                set(
                  "digest_times",
                  form.digest_times.filter((t) => t !== time)
                )
              }
              className="bg-brand rounded-full px-4 py-2 mr-2 mb-2"
            >
              <Text className="text-brand-ink text-sm font-semibold">{time} ✕</Text>
            </Pressable>
          ))}
          <Pressable onPress={() => setShowTimePicker(true)} className="bg-surface border border-line rounded-full px-4 py-2 mb-2">
            <Text className="text-ink text-sm font-semibold">+ Add time</Text>
          </Pressable>
        </View>

        {showTimePicker ? (
          <DateTimePicker
            value={new Date()}
            mode="time"
            is24Hour
            onChange={(_, date) => {
              setShowTimePicker(Platform.OS === "ios");
              if (date) addTime(date);
            }}
          />
        ) : null}
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 bg-background border-t border-line px-4 pt-3 pb-6">
        <Button label="Save" onPress={save} loading={saveMutation.isPending} />
      </View>
    </View>
  );
}

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
        value={String(value)}
        onChangeText={(t) => {
          const n = parseInt(t.replace(/[^0-9]/g, ""), 10);
          onChange(Number.isNaN(n) ? 0 : n);
        }}
        keyboardType="number-pad"
        className="bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink"
      />
    </View>
  );
}
