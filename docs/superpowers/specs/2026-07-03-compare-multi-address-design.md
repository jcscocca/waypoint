# Compare-first flagship — slice B: multi-address compare UX — design

**Date:** 2026-07-03
**Status:** Approved pending user spec review
**Roadmap:** Phase 5 (compare-first flagship) — **slice B of three**. Slice A (richer
payload-driven verdicts) shipped in #94/#95. Slice C (comparison-first landing) is later.

## Why

Slice A made the compare *result* strong. But to compare, you still assemble the set on the
**Places tab** (add pins / search there, select ≥2), then switch to Compare. Slice B closes
that gap: a Compare-owned control to **build and edit the comparison set in place** — the
natural "I have three candidate apartments, line them up" flow — so Compare stops depending
on a detour through Places.

The engine and the verdict UI are already N-way (slice A), so this slice is **frontend
only, no backend change**: it reuses the existing stateless inline-`points` compare path
(`/dashboard/compare` accepts `points`, ≤10, Seattle-bbox validated) that slice A already
proved out for shared views.

## Goal

Give the Compare tab an editable, ephemeral **compare set** — add an address via search,
remove a row, re-run — driving the slice-A verdict, without touching saved Places.

## Design decisions (settled in brainstorm)

1. **Ephemeral scratchpad, not saved Places.** Addresses added in Compare are candidates
   you're evaluating. They geocode into an in-memory set of `points`
   (`{latitude, longitude, label}`) and run through the inline-points compare path. They are
   **not** persisted as Place entities and do not appear in the Places list.
2. **Seeded from the current selection.** Opening Compare with places already selected (from
   Places / the map) or from a shared `?view=` link pre-fills the set, so the existing
   "select then Compare" flow still works. From there the user edits freely.
3. **Decoupled.** Add/remove in Compare does **not** change the Places-tab selection
   (`selectedIds`) or saved Places — the compare set is Compare-local once seeded. (Rejected
   alternative: coupling the set to the workspace selection so edits ripple to map markers —
   entangles the tabs and muddies the throwaway-candidate model.)
4. **Explicit re-run.** Editing the set marks the current verdict stale; the user clicks
   Compare to recompute (matches today's button; no request per keystroke).
5. **Bounds.** 2–10 addresses (the inline-points cap `_MAX_POINTS`), each Seattle-bbox
   guarded — same limits slice A already enforces.

## Product invariant

Unchanged and unaffected: the rendered verdict is slice A's (ranked by reported-incident
rate, callout bounded to statistical clarity, guard test in place). Slice B only changes how
the *input set* is assembled; it adds no ranking or safety language.

## Architecture

Frontend only. New/edited units:

- **`useCompareSet` (new hook, `frontend/src/lib/`)** — owns the editable compare set:
  `points: ComparePoint[]`, `add(point)`, `removeAt(index)` / `remove(id)`, and a
  `seed(selected)` that initializes the set from the current `selected` places (converting
  each to `{latitude, longitude, label}`). Since MapWorkspace already synthesizes `selected`
  from a shared `?view=` when one is present, seeding from `selected` covers both normal
  selection and shared links — no separate shared-view branch. Tracks a "user-edited"
  flag so re-seeding on selection change only happens before the user's first manual edit
  (after that the set is theirs). Enforces the ≤10 cap and de-dupes by rounded coordinate.
  This is the testable core of the slice.
- **`CompareAddressInput` (new component)** — the add control. Wraps the existing
  `useAddressSearch` hook (the shared geocode/type-ahead/Seattle-guard/recent-history hook
  that Places search already uses); on selecting a result it calls `add(point)`. Disabled at
  10. Surfaces geocode-not-found / out-of-Seattle errors inline via the hook's existing
  states.
- **`CompareTab` (edited)** — renders, above the slice-A verdict: the "Addresses to compare ·
  N of 10" label, the `CompareAddressInput`, and the removable numbered rows; keeps the
  Compare button (now runs the current set). When the set is stale-since-last-run, the button
  reads "Compare N addresses" and a subtle "edited — re-run to update" note shows.
- **`useCompare` (edited, minimal)** — already accepts a `points` override and runs it when
  `length ≥ 2`; slice B feeds it the `useCompareSet` points instead of only the shared-view
  points. `versionRef` stale-guard and `applyAssistant` preserved.
- **`MapWorkspace` (edited, wiring)** — owns/holds `useCompareSet` (seeded from `selected` /
  `sharedPoints`), passes its points to `useCompare` and the set + add/remove callbacks to
  `CompareTab`.
- **Shareability** — the set is `points`, so the existing `buildShareUrl("compare")` /
  `savedView` encoding continues to capture it unchanged; a shared link still round-trips.

`ComparePoint` = `{ latitude: number; longitude: number; label: string }` (the existing
inline-point shape used by `useCompare`/`client.ts`/`savedView`).

## Data flow

address search (`useAddressSearch`) → selected result → `useCompareSet.add(point)` → set
updates, verdict marked stale → user clicks Compare → `useCompare.runCompare()` POSTs the
`points` to `/dashboard/compare` → `SiteComparison` → slice-A verdict renders on the set. No
new network shape; no persistence writes.

Because the set is always `points`, Compare runs the inline-points path uniformly — even for
addresses seeded from saved places (their coords become points). For the same coordinates the
returned `SiteComparison` is identical to the persisted `place_ids` path, and slice A renders
purely from that payload, so nothing is lost by dropping the `place_ids` path from Compare.

## States & edge cases

- **< 2 in set:** verdict area shows the existing "add at least two addresses to compare"
  prompt; Compare disabled.
- **At 10:** the add input is disabled with a "10 max" hint.
- **Geocode miss / outside Seattle:** inline error from `useAddressSearch`; the set is
  unchanged.
- **Duplicate address:** de-duped by rounded coordinate (no-op add, brief hint).
- **Edited-since-run:** verdict kept but marked stale; re-run refreshes it. Removing a row
  below 2 disables Compare until another is added.
- **Seeded set, then selection changes:** re-seeds only if the user hasn't manually edited
  (the "user-edited" flag); otherwise the user's set stands.

## Testing

- `useCompareSet.test.ts` (pure): add / remove / seed-from-selected / seed-from-points; the
  user-edited flag gating re-seed; ≤10 cap; coordinate de-dupe; ordering.
- `CompareAddressInput.test.tsx`: selecting a search result adds a point; disabled at 10;
  surfaces the geocode/out-of-bbox error state.
- `CompareTab.test.tsx` (extended): renders the editor + rows; remove drops a row; the "N of
  10" count; the stale/re-run affordance; < 2 gating; slice-A verdict still renders for a set
  of ≥ 2. Invariant guard from slice A stays green (verdict copy unchanged).
- `make test-all` green.

## File structure

- **Create:** `frontend/src/lib/useCompareSet.ts` (+ `.test.ts`),
  `frontend/src/components/CompareAddressInput.tsx` (+ `.test.tsx`).
- **Modify:** `frontend/src/components/CompareTab.tsx` (+ its test), `frontend/src/lib/useCompare.ts`
  (feed the editable points), `frontend/src/components/MapWorkspace.tsx` (own/seed the set,
  wire it), and the Compare CSS block for the editor rows/input.
- **No backend / `app/` change.** No new endpoint, schema, or migration.

## Out of scope (deferred / tracked)

- **Rendering the ephemeral compare set on the map.** Nice for spatial context and the
  shared-view points path already renders points, so it's a cheap follow-up — but not a goal
  here; slice B keeps the set in the Compare panel to hold the decoupled-scratchpad model
  clean.
- **Persisting a compare address to Places** (a "save this candidate" affordance) — possible
  later; the ephemeral default stands.
- **Auto-run on edit** (vs the explicit re-run chosen here).
- **Slice C** (comparison-first landing).

## Sequencing

Single PR from the `compare-multi-address` worktree, gated on `make test-all`. TDD-first on
`useCompareSet` (the editable-set logic), then `CompareAddressInput`, then the `CompareTab`
integration and wiring, then a ROADMAP slice-B tick.
