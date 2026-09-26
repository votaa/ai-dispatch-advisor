# POC-050 — Crew operating-HQ map resolution contract

## Purpose and scope

Resolve known synthetic Long Island RDA and vegetation staging labels to an operating-HQ **map proxy** so those crews can be found on Operations Map. Preserve `current_location` exactly as supplied. The proxy represents division affiliation at a village center; it does not claim the crew, staging area, or HQ building is physically at that point.

This contract covers map presentation only. It does not change crew status, assignments, home region, dispatch decisions, recommendation scoring, or travel estimates. The fictional locations in the `base`, `storm`, `crew-shortage`, and `critical-facility` fixtures remain unmapped.

## Current evidence (2026-09-25)

`CrewService` currently calls `GeographyRegistry.resolve(current_location)` and returns `map_location: null` for unknown names. The registry provides village-center coordinates and stable reference IDs. The generator has an explicit division-to-RDA list and four division service locations. Across the current scenario CSVs, 183 RDA records and 40 vegetation staging records are unresolved: 45 RDA plus 10 vegetation in `august-storm-preview-v3`, and 138 RDA plus 30 vegetation in `september-storm-preview-v2`. No RDA record has a conflicting `home_region` in those files. These counts describe the checked-in snapshot, not an invariant for future scenarios.

## Controlled map-proxy mapping

Use an exact, normalized full-label match against the controlled staging list below. Normalization may ignore case and repeated punctuation/spacing, as the geography registry does; it must not accept an arbitrary RDA number, fuzzy place name, or substring. Require `home_region` to equal the listed division before resolving. Each target is an existing named village-center record in `LongIslandGeography.csv`; use its stable `reference_id` and coordinates, never a newly invented HQ coordinate.

| Crew `current_location` | Required `home_region` | Map proxy village | Registry reference ID |
| --- | --- | --- | --- |
| `RDA1 MUA Staging`; `Hewlett Vegetation Staging Area` | `Queens-Nassau` | Hewlett | `pseg-li-78b452f119b7098c48bb` |
| `RDA4 MUA Staging`; `RDA7 MUA Staging`; `Hicksville Vegetation Staging Area` | `Central-Nassau` | Hicksville | `pseg-li-32180e1a9c9aeac831db` |
| `RDA10 MUA Staging`; `RDA13 MUA Staging`; `Brentwood Vegetation Staging Area` | `Western Suffolk` | Brentwood | `pseg-li-19dde346bc11e762bd90` |
| `RDA16 MUA Staging`; `RDA19 MUA Staging`; `Riverhead Vegetation Staging Area` | `Eastern Suffolk` | Riverhead | `pseg-li-808d36974b333bb1ab63` |

## Resolution order and failure behavior

1. Resolve `current_location` through the existing geography registry first. Keep the existing `village_center` result for a directly recognized place, regardless of `home_region`; a crew may be working outside its home division.
2. If direct resolution fails, look up the full staging label in the controlled mapping and verify that `home_region` matches. Resolve the mapped village through the registry by reference ID or an equivalently validated stable identity.
3. If the label is missing, the division conflicts, the target reference is missing or ambiguous, or the coordinate is invalid, return `map_location: null`. Retain the record in unmapped counts and lists with its original `current_location`. Do not fall back to `home_region` alone.

The controlled mapping is a reviewed synthetic-scenario convention. A future source-derived RDA mapping needs its own provenance and approval. Validation should ensure every controlled label is unique and every target reference exists in the loaded registry; a broken mapping must fail closed and be visible in diagnostics.

## API and operator presentation

Keep `Crew.current_location` unchanged. Extend `CrewMapLocation` with a backward-compatible resolution basis, such as `source_place` or `operating_hq_proxy`. Retain `precision: village_center` for both, since the coordinate is a village center. For a proxy, expose the target village and reference ID plus a human-readable basis label. Older responses lacking the new field should continue to render as the existing approximate village-center location.

On Operations Map, label a proxy selection or marker detail **“Operating HQ proxy: Hewlett (approximate village center)”** (or the corresponding village), followed by **“Reported location: RDA1 MUA Staging.”** Directly resolved places retain their existing approximate-center language. Search and result rows should continue to include the original location name; filters, counts, selection, and Show on map use the resolved marker but must not describe it as a live crew position or the actual staging-area coordinate.

## Implementation and acceptance slice

1. Add a dedicated map-location resolver beside the geography registry. Keep the shared `GeographyRegistry.resolve` and `TravelEstimateService` behavior unchanged; adding staging aliases to the general geography registry would change unrelated location and travel semantics.
2. Add the resolution-basis field to the backend model and frontend type, and update the map's detail copy for proxies.
3. Cover every listed label and target reference, region mismatch, unknown RDA number, unknown division, missing target, direct place resolution, and legacy API responses. Verify that `current_location` is unchanged and no travel/recommendation result changes.
4. Check both large Long Island scenarios: the current 223 known staging records become mapped, while unrelated fictional or unknown locations remain unmapped. Reconcile complete-inventory and filtered mapped/unmapped counts; inspect desktop and narrow layouts plus Show on map for a proxy crew.

Do not regenerate checked-in scenario CSVs merely to implement this read-time map resolution. The POC remains open until implementation and validation are reviewed.
