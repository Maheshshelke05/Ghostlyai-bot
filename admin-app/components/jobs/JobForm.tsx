import { zodResolver } from "@hookform/resolvers/zod";
import { BottomSheetModal } from "@gorhom/bottom-sheet";
import DateTimePicker from "@react-native-community/datetimepicker";
import { useQuery } from "@tanstack/react-query";
import * as Clipboard from "expo-clipboard";
import * as Haptics from "expo-haptics";
import { useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { SelectSheet } from "@/components/ui/SelectSheet";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, listCategories, type JobIn } from "@/lib/api";

const schema = z.object({
  title: z.string().min(2).max(200),
  company: z.string().min(1).max(160),
  category_slug: z.string().min(1, "Category is required"),
  qualification: z.string().max(200).optional().or(z.literal("")),
  location_text: z.string().max(160).optional().or(z.literal("")),
  job_type: z.enum(["govt", "private", "internship", "wfh"]),
  salary: z.string().max(80).optional().or(z.literal("")),
  apply_link: z.string().url("Enter a valid URL"),
  last_date: z.string().optional().or(z.literal("")),
  description: z.string().max(1000).optional().or(z.literal("")),
});
export type JobFormData = z.infer<typeof schema>;

const JOB_TYPES: { value: JobFormData["job_type"]; label: string }[] = [
  { value: "govt", label: "🏛 Government" },
  { value: "private", label: "🏢 Private" },
  { value: "internship", label: "🎓 Internship" },
  { value: "wfh", label: "🏠 WFH" },
];

interface JobFormProps {
  defaultValues?: Partial<JobFormData>;
  submitLabel?: string;
  showSaveAndNew?: boolean;
  onSubmit: (data: JobIn) => Promise<void>;
  onSubmitAndNew?: (data: JobIn) => Promise<void>;
}

export function JobForm({
  defaultValues,
  submitLabel = "Save",
  showSaveAndNew = false,
  onSubmit,
  onSubmitAndNew,
}: JobFormProps) {
  const { show } = useToast();
  const [submitting, setSubmitting] = useState<"save" | "save-new" | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const categorySheetRef = useRef<BottomSheetModal>(null);

  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  const {
    control,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<JobFormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      job_type: "private",
      ...defaultValues,
    },
  });

  const categorySlug = watch("category_slug");
  const lastDate = watch("last_date");

  const categoryOptions = (categories ?? []).map((c) => ({ label: c.name, value: c.slug }));

  const toJobIn = (data: JobFormData): JobIn => ({
    title: data.title.trim(),
    company: data.company.trim(),
    category_slug: data.category_slug,
    qualification: data.qualification || null,
    location_text: data.location_text || null,
    job_type: data.job_type,
    salary: data.salary || null,
    apply_link: data.apply_link.trim(),
    last_date: data.last_date || null,
    description: data.description || null,
  });

  const submit = async (mode: "save" | "save-new") => {
    await handleSubmit(async (data) => {
      setSubmitting(mode);
      try {
        if (mode === "save-new" && onSubmitAndNew) {
          await onSubmitAndNew(toJobIn(data));
          reset({ job_type: data.job_type, category_slug: data.category_slug });
          show("Job saved", "success");
        } else {
          await onSubmit(toJobIn(data));
        }
      } catch (err) {
        show(apiErrorMessage(err, "Could not save the job"), "error");
      } finally {
        setSubmitting(null);
      }
    })();
  };

  const pasteLink = async () => {
    const text = await Clipboard.getStringAsync();
    if (text) setValue("apply_link", text.trim());
  };

  const selectedCategoryLabel = categoryOptions.find((c) => c.value === categorySlug)?.label;

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
      <FieldLabel text="Title *" />
      <Controller
        control={control}
        name="title"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput value={value} onChangeText={onChange} onBlur={onBlur} placeholder="Junior Accountant" className={inputClass} />
        )}
      />
      <FieldError message={errors.title?.message} />

      <FieldLabel text="Company *" />
      <Controller
        control={control}
        name="company"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput value={value} onChangeText={onChange} onBlur={onBlur} placeholder="Shree Traders Pvt Ltd" className={inputClass} />
        )}
      />
      <FieldError message={errors.company?.message} />

      <FieldLabel text="Category *" />
      <Pressable onPress={() => categorySheetRef.current?.present()} className={inputClass}>
        <Text className={selectedCategoryLabel ? "text-ink" : "text-muted"}>
          {selectedCategoryLabel ?? "Select category"}
        </Text>
      </Pressable>
      <FieldError message={errors.category_slug?.message} />

      <FieldLabel text="Job type" />
      <View className="flex-row flex-wrap mb-1">
        {JOB_TYPES.map((jt) => (
          <Chip key={jt.value} label={jt.label} selected={watch("job_type") === jt.value} onPress={() => setValue("job_type", jt.value)} />
        ))}
      </View>

      <FieldLabel text="Location (city / area)" />
      <Controller
        control={control}
        name="location_text"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput value={value} onChangeText={onChange} onBlur={onBlur} placeholder="e.g. Andheri, Mumbai" className={inputClass} />
        )}
      />

      <FieldLabel text="Qualification" />
      <Controller
        control={control}
        name="qualification"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput value={value} onChangeText={onChange} onBlur={onBlur} placeholder="B.Com, Tally" className={inputClass} />
        )}
      />

      <FieldLabel text="Salary" />
      <Controller
        control={control}
        name="salary"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput value={value} onChangeText={onChange} onBlur={onBlur} placeholder="₹12,000 - ₹15,000" className={inputClass} />
        )}
      />

      <FieldLabel text="Apply link *" />
      <View className="flex-row items-center gap-2 mb-1">
        <Controller
          control={control}
          name="apply_link"
          render={({ field: { onChange, value, onBlur } }) => (
            <TextInput
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              placeholder="https://..."
              autoCapitalize="none"
              className={`${inputClass} flex-1 mb-0`}
            />
          )}
        />
        <Pressable onPress={pasteLink} className="bg-line/60 rounded-xl px-3 py-3.5">
          <Text className="text-xs font-semibold text-ink">Paste</Text>
        </Pressable>
      </View>
      <FieldError message={errors.apply_link?.message} />

      <FieldLabel text="Last date" />
      <Pressable onPress={() => setShowDatePicker(true)} className={inputClass}>
        <Text className={lastDate ? "text-ink" : "text-muted"}>{lastDate || "Select date (optional)"}</Text>
      </Pressable>
      {showDatePicker ? (
        <DateTimePicker
          value={lastDate ? parseLocalDate(lastDate) : new Date()}
          mode="date"
          onChange={(_, date) => {
            setShowDatePicker(Platform.OS === "ios");
            if (date) setValue("last_date", toLocalDateString(date));
          }}
        />
      ) : null}

      <FieldLabel text="Description" />
      <Controller
        control={control}
        name="description"
        render={({ field: { onChange, value, onBlur } }) => (
          <TextInput
            value={value}
            onChangeText={onChange}
            onBlur={onBlur}
            placeholder="2 openings, Saturday half day"
            multiline
            numberOfLines={3}
            className={`${inputClass} h-20`}
            style={{ textAlignVertical: "top" }}
          />
        )}
      />

      <View className="mt-4 gap-3">
        <Button label={submitLabel} onPress={() => submit("save")} loading={submitting === "save"} variant="primary" />
        {showSaveAndNew ? (
          <Button
            label="Save & add another"
            onPress={() => submit("save-new")}
            loading={submitting === "save-new"}
            variant="ghost"
          />
        ) : null}
      </View>

      <SelectSheet
        ref={categorySheetRef}
        title="Select category"
        options={categoryOptions}
        onSelect={(value) => {
          setValue("category_slug", value);
          Haptics.selectionAsync().catch(() => {});
          categorySheetRef.current?.dismiss();
        }}
      />
    </ScrollView>
  );
}

const inputClass = "bg-surface border border-line rounded-2xl px-4 py-3.5 text-ink mb-1";

// Build YYYY-MM-DD from the phone's local calendar date. toISOString() converts to UTC first,
// so anything picked between 00:00 and 05:30 IST came out as the previous day.
function toLocalDateString(date: Date): string {
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${mm}-${dd}`;
}

// new Date("YYYY-MM-DD") parses as UTC midnight; construct it as a local date instead
function parseLocalDate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

function FieldLabel({ text }: { text: string }) {
  return <Text className="text-sm font-semibold text-muted mb-1.5 mt-3">{text}</Text>;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <Text className="text-danger text-xs mb-1">{message}</Text>;
}
