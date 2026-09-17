import { Text, View } from "react-native";

import { formatValue, humanizeKey, isPlainObject, type AnyRecord } from "@/lib/ghostlyFormat";
import { Card } from "./Card";

/** Generic "everything this object has" renderer, used for GhostlyAI.in data whose exact
 * field names aren't confirmed yet: whatever the API actually returns still shows up here,
 * even if a screen's hand-picked "nice" fields above it guessed the wrong key name. */
export function KeyValueList({
  data,
  hideKeys = [],
  title,
}: {
  data: AnyRecord;
  hideKeys?: string[];
  title?: string;
}) {
  const hidden = new Set(hideKeys.map((k) => k.toLowerCase()));
  const entries = Object.entries(data).filter(([k]) => !hidden.has(k.toLowerCase()));
  if (entries.length === 0) return null;

  return (
    <Card className="mb-3">
      {title ? <Text className="text-[13px] font-semibold text-muted mb-2 uppercase tracking-wide">{title}</Text> : null}
      {entries.map(([key, value], i) => (
        <View key={key} className={i > 0 ? "mt-3 pt-3 border-t border-line" : ""}>
          <Text className="text-[13px] text-muted mb-0.5">{humanizeKey(key)}</Text>
          {isPlainObject(value) ? (
            <View className="mt-1 pl-3 border-l-2 border-line">
              {Object.entries(value).map(([k2, v2]) => (
                <View key={k2} className="mb-1.5">
                  <Text className="text-[12px] text-muted">{humanizeKey(k2)}</Text>
                  <Text className="text-[15px] text-ink">{formatValue(k2, v2)}</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text className="text-[16px] text-ink">{formatValue(key, value)}</Text>
          )}
        </View>
      ))}
    </Card>
  );
}
