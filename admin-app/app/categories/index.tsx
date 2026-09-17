import { BottomSheetBackdrop, BottomSheetModal, BottomSheetTextInput, BottomSheetView } from "@gorhom/bottom-sheet";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { forwardRef, useCallback, useEffect, useRef, useState } from "react";
import { FlatList, Pressable, Switch, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { apiErrorMessage, createCategory, listCategories, updateCategory, type CategoryOut } from "@/lib/api";
import { useIsOwner } from "@/store/auth";

export default function CategoriesScreen() {
  const isOwner = useIsOwner();
  const { show } = useToast();
  const queryClient = useQueryClient();
  const sheetRef = useRef<BottomSheetModal>(null);
  const [editing, setEditing] = useState<CategoryOut | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ["categories"], queryFn: listCategories });

  const toggleMutation = useMutation({
    mutationFn: (cat: CategoryOut) => updateCategory(cat.id, { is_active: !cat.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
    onError: (err) => show(apiErrorMessage(err), "error"),
  });

  const renderBackdrop = useCallback(
    (props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />,
    []
  );

  if (isLoading) {
    return (
      <View className="flex-1 bg-background pt-4">
        <ListSkeleton />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-background">
      <FlatList
        data={data ?? []}
        keyExtractor={(c) => String(c.id)}
        contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => {
              if (!isOwner) return;
              setEditing(item);
              sheetRef.current?.present();
            }}
            className="bg-surface rounded-2xl p-4 mb-2 flex-row items-center justify-between active:opacity-70"
          >
            <View className="flex-1 pr-2">
              <Text className="text-base font-semibold text-ink">{item.name}</Text>
              <Text className="text-xs text-muted mt-0.5">
                {item.slug} • {item.jobs_count} active jobs • {item.users_count} users
              </Text>
            </View>
            {isOwner ? (
              <Switch value={item.is_active} onValueChange={() => toggleMutation.mutate(item)} />
            ) : (
              <Text className="text-xs text-muted">{item.is_active ? "Active" : "Off"}</Text>
            )}
          </Pressable>
        )}
      />

      {isOwner ? (
        <View className="absolute bottom-6 left-4 right-4">
          <Button
            label="+ New category"
            variant="brand"
            onPress={() => {
              setEditing(null);
              sheetRef.current?.present();
            }}
          />
        </View>
      ) : null}

      <CategoryEditSheet ref={sheetRef} category={editing} renderBackdrop={renderBackdrop} />
    </View>
  );
}

const CategoryEditSheet = forwardRef<
  BottomSheetModal,
  { category: CategoryOut | null; renderBackdrop: (props: any) => React.ReactElement }
>(function CategoryEditSheet({ category, renderBackdrop }, ref) {
  const { show } = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState(category?.name ?? "");
  const [nameMr, setNameMr] = useState(category?.name_mr ?? "");
  const [nameHi, setNameHi] = useState(category?.name_hi ?? "");
  const [slug, setSlug] = useState(category?.slug ?? "");
  const [loading, setLoading] = useState(false);

  // Reset fields whenever the sheet is opened for a (possibly different) category.
  useEffect(() => {
    setName(category?.name ?? "");
    setNameMr(category?.name_mr ?? "");
    setNameHi(category?.name_hi ?? "");
    setSlug(category?.slug ?? "");
  }, [category]);

  const submit = async () => {
    if (!name.trim()) {
      show("Enter a name", "warn");
      return;
    }
    const normalizedSlug = slug.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    if (!category && !normalizedSlug) {
      show("Enter a valid slug (e.g. banking)", "warn");
      return;
    }
    setLoading(true);
    try {
      if (category) {
        await updateCategory(category.id, { name: name.trim(), name_mr: nameMr, name_hi: nameHi });
      } else {
        await createCategory({ slug: normalizedSlug, name: name.trim(), name_mr: nameMr, name_hi: nameHi });
      }
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      show("Category saved", "success");
      (ref as React.RefObject<BottomSheetModal>).current?.dismiss();
    } catch (err) {
      show(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <BottomSheetModal ref={ref} snapPoints={["55%"]} backdropComponent={renderBackdrop}>
      <BottomSheetView className="px-5 pb-8 pt-2">
        <Text className="text-lg font-bold text-ink mb-4">{category ? "Edit category" : "New category"}</Text>

        {!category ? (
          <>
            <Text className="text-xs font-semibold text-muted mb-1">Slug (permanent, e.g. banking)</Text>
            <BottomSheetTextInput
              value={slug}
              onChangeText={setSlug}
              autoCapitalize="none"
              className="bg-background rounded-xl px-4 py-3 text-ink mb-3"
            />
          </>
        ) : null}

        <Text className="text-xs font-semibold text-muted mb-1">Name (English)</Text>
        <BottomSheetTextInput value={name} onChangeText={setName} className="bg-background rounded-xl px-4 py-3 text-ink mb-3" />

        <Text className="text-xs font-semibold text-muted mb-1">Name (Marathi)</Text>
        <BottomSheetTextInput value={nameMr} onChangeText={setNameMr} className="bg-background rounded-xl px-4 py-3 text-ink mb-3" />

        <Text className="text-xs font-semibold text-muted mb-1">Name (Hindi)</Text>
        <BottomSheetTextInput value={nameHi} onChangeText={setNameHi} className="bg-background rounded-xl px-4 py-3 text-ink mb-4" />

        <Button label="Save" onPress={submit} loading={loading} />
      </BottomSheetView>
    </BottomSheetModal>
  );
});
