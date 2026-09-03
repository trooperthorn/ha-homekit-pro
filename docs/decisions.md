# Decisions

## Undated: lowercase homekit_id storage workaround

An earlier version of this integration stored a pairing's `homekit_id` in
the entity-map storage cache in lowercase for some pairings. `async_delete_map`
checks both the stored ID and its lowercased form when deleting a cache
entry, so a cache entry written under the old lowercase behavior is still
found and removed. The workaround stays until the storage format is
verified clean of lowercase-keyed entries across all installs, which cannot
be confirmed from this repository alone.
