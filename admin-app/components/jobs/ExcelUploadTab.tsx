import * as DocumentPicker from "expo-document-picker";
import { Directory, File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, bulkTemplateUrl, bulkUploadJobs, type BulkResult } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export function ExcelUploadTab() {
  const token = useAuthStore((s) => s.token);
  const { show } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<BulkResult | null>(null);

  const downloadTemplate = async () => {
    setDownloading(true);
    try {
      const file = await File.downloadFileAsync(bulkTemplateUrl(), new Directory(Paths.cache), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        idempotent: true,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(file.uri, { mimeType: "text/csv" });
      } else {
        show(`Template saved: ${file.uri}`, "success");
      }
    } catch (err) {
      show(apiErrorMessage(err, "Could not download the template"), "error");
    } finally {
      setDownloading(false);
    }
  };

  const pickAndUpload = async () => {
    const picked = await DocumentPicker.getDocumentAsync({
      type: [
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
      ],
      copyToCacheDirectory: true,
    });
    if (picked.canceled || !picked.assets?.[0]) return;

    const asset = picked.assets[0];
    setUploading(true);
    setResult(null);
    try {
      const res = await bulkUploadJobs({ uri: asset.uri, name: asset.name, mimeType: asset.mimeType });
      setResult(res);
    } catch (err) {
      show(apiErrorMessage(err, "Upload failed"), "error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <View className="p-4">
      <Text className="text-sm text-muted mb-3">
        Download the template, fill in your jobs, then upload the file. Columns: title, company,
        category_slug, qualification, location_text, job_type, salary, apply_link,
        last_date, description.
      </Text>

      <Button label="📄 Download template" variant="ghost" onPress={downloadTemplate} loading={downloading} />

      <View className="h-3" />

      <Button label="📤 Choose file & upload" variant="brand" onPress={pickAndUpload} loading={uploading} />

      {uploading ? (
        <View className="items-center mt-6">
          <ActivityIndicator />
          <Text className="text-muted text-sm mt-2">Processing...</Text>
        </View>
      ) : null}

      {result ? (
        <View className="mt-6 flex-row gap-3">
          <ResultStat label="Created" value={result.created} tone="text-go" />
          <ResultStat label="Duplicates" value={result.duplicates} tone="text-info" />
          <ResultStat label="Errors" value={result.errors.length} tone="text-danger" />
        </View>
      ) : null}

      {result && result.errors.length > 0 ? (
        <View className="mt-4">
          {result.errors.map((e, i) => (
            <Text key={i} className="text-xs text-danger mb-1">
              Row {e.row ?? e.index}: {e.error}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function ResultStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <View className="flex-1 items-center bg-surface rounded-2xl py-3">
      <Text className={`text-xl font-extrabold ${tone}`}>{value}</Text>
      <Text className="text-xs text-muted mt-0.5">{label}</Text>
    </View>
  );
}
