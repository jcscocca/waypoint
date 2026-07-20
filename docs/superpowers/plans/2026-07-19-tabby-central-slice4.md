# Tabby-Central Slice 4: Presence Badges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analyzed pins get a neutral presence badge (server-described, never verdict-bearing) that taps through to the place's latest analysis card; new analyses fit the camera around the analyzed places with drawer-aware padding.

**Architecture:** `_analyze_places`/`_compare_places` gain a `badges` descriptor list (place_id, label, run_id, settings fingerprint) built from a bulk `PlaceCluster` lookup (UI-path resolution carries bare ids — survey confirmed `matched`/`created` are empty there). The bridge parses it into the effect; `MapWorkspace` owns `liveBadges` (replaced per analysis, cleared with `invalidateAnalysisContext`/delete). `MapCanvas` renders badges as real DOM child nodes on the existing marker elements (markers are DOM, `markerElsRef` maps ids) with a distinct stop-propagated click → scroll the thread to that place's newest card (mobile: expand the sheet first). A new `fitTo` prop drives `map.fitBounds` with right-padding from the drawer width on desktop / bottom padding on mobile (no `fitBounds` exists in the repo today).

**Tech Stack:** FastAPI (descriptor block), MapLibre DOM markers, React 18 + Vitest.

**Spec:** `docs/superpowers/specs/2026-07-19-tabby-central-redesign-design.md` (Slice 4). Product invariant: badges are presence-only — no verdict text, arrows, or evaluative color. Badge copy: "Analyzed — view context".

**Worktree:** dedicated worktree from `main`; `make install` + `npm install` once. Gates as previous slices.

---

## File structure

| File | Status | Responsibility |
| --- | --- | --- |
| `app/assistant/tools.py` (+`tests/test_assistant_tools.py`) | modify | `_badge_descriptors` helper + `badges` in both results |
| `frontend/src/types.ts` | modify | `BadgeDescriptor`; effect + card gain `badges` |
| `frontend/src/lib/assistantBridge.ts` (+test) | modify | parse `result.badges` into the effect |
| `frontend/src/components/MapCanvas.tsx` (+test) | modify | `badgedPlaceIds` + `onBadgeClick` props; DOM badge node; `fitTo` prop |
| `frontend/src/components/AssistantPanel.tsx` (+test) | modify | `focusCard` scroll-into-view |
| `frontend/src/components/MapWorkspace.tsx` (+test) | modify | `liveBadges` state, badge-tap routing, fit-on-analysis |
| `frontend/src/styles/mapWorkspace.css` | modify | `.mc-pin-presence` (monochrome) |

---

### Task 1: Backend — `badges` descriptor block

**Files:** Modify `app/assistant/tools.py`; test `tests/test_assistant_tools.py`.

- [ ] **Step 1: Failing tests** (mirror the existing analyze/compare test setups in the file — same fixtures/args as the run-id tests added in slice 3):

```python
def test_analyze_places_returns_badge_descriptors(...same fixtures as the run-id test...):
    result = execute_tool(session, user_hash, "analyze_places", {...same args...})
    payload = result["result"]
    badges = payload["badges"]
    assert [b["place_id"] for b in badges] == payload["place_ids"]
    badge = badges[0]
    assert badge["run_id"] == payload["analysis_run_id"]
    assert badge["label"]  # real display label from PlaceCluster
    assert len(badge["settings_fingerprint"]) == 12
    # Same settings → same fingerprint; different radius → different fingerprint.
    again = execute_tool(session, user_hash, "analyze_places", {...same args...})
    assert again["result"]["badges"][0]["settings_fingerprint"] == badge["settings_fingerprint"]


def test_compare_places_returns_badge_descriptors(...):
    result = execute_tool(session, user_hash, "compare_places", {...same args as the compare run-id test...})
    payload = result["result"]
    assert {b["place_id"] for b in payload["badges"]} == set(payload["place_ids"])
```

- [ ] **Step 2: Verify fail**, then implement in `tools.py`:

```python
def _badge_descriptors(
    session: Session,
    place_ids: list[str],
    run_id: str | None,
    settings_used: dict[str, Any],
) -> list[dict[str, Any]]:
    # Neutral presence descriptors: which places have current results, and from
    # which run/settings. Never carries verdict content (product invariant).
    fingerprint = hashlib.sha256(
        json.dumps(settings_used, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    rows = session.execute(
        select(PlaceCluster).where(PlaceCluster.id.in_(place_ids))
    ).scalars()
    labels = {row.id: row.display_label for row in rows}
    return [
        {
            "place_id": place_id,
            "label": labels.get(place_id, ""),
            "run_id": run_id,
            "settings_fingerprint": fingerprint,
        }
        for place_id in place_ids
    ]
```

(Imports: `hashlib`, `json` — check what the module already imports; `select` and `PlaceCluster` are already used by `_add_place`'s pattern.) In `_analyze_places` and `_compare_places`, after the `run_id` capture, compute `settings_used = _settings_used(...)` ONCE (both functions already call it in the result dict — hoist to a local so the fingerprint and the result share the same dict) and add `"badges": _badge_descriptors(session, resolved.place_ids, run_id, settings_used)` to both result dicts.

- [ ] **Step 3: Pass** (full backend suite + ruff), **commit**: `feat(assistant): neutral badge descriptors on analyze/compare results`

---

### Task 2: Frontend — descriptor type, bridge parse, workspace badge state

**Files:** Modify `frontend/src/types.ts`, `frontend/src/lib/assistantBridge.ts` (+test), `frontend/src/components/MapWorkspace.tsx` (+test in Task 4's pass).

- [ ] **Step 1:** `types.ts`:

```ts
export type BadgeDescriptor = {
  place_id: string;
  label: string;
  run_id: string | null;
  settings_fingerprint: string;
};
```

`AssistantToolEffect` gains `badges?: BadgeDescriptor[]`. `AnalysisCardData` is unchanged (cards already carry placeIds/runId).

- [ ] **Step 2 (TDD):** bridge test — analyze/compare results with a `badges` array surface it on the effect verbatim; missing/malformed (`badges` not an array) → effect has no `badges` key. Implement in both bridge cases:

```ts
...(Array.isArray(result.badges) ? { badges: result.badges as BadgeDescriptor[] } : {}),
```

- [ ] **Step 3:** `MapWorkspace`: `const [liveBadges, setLiveBadges] = useState<Map<string, BadgeDescriptor>>(new Map());`
  - In `applyAssistantToolResult`: `if (effect.badges) setLiveBadges(new Map(effect.badges.map((b) => [b.place_id, b])));` (replace semantics — the newest analysis defines "current").
  - `invalidateAnalysisContext()` additionally does `setLiveBadges(new Map());` (filter changes detach badges, per spec).
  - `handleDelete(id)` removes the entry: `setLiveBadges((current) => { if (!current.has(id)) return current; const next = new Map(current); next.delete(id); return next; });`
  - Pass `badgedPlaceIds={new Set(liveBadges.keys())}` to `MapCanvas` (prop added in Task 3; keep this wiring commented out or behind the prop's existence until Task 3 lands if you're committing separately — these two tasks may land as one commit if cleaner: message `feat(rail): badge descriptors flow to workspace state`).

---

### Task 3: `MapCanvas` — presence badge nodes + `fitTo`

**Files:** Modify `frontend/src/components/MapCanvas.tsx` (+test), `frontend/src/styles/mapWorkspace.css`.

- [ ] **Step 1 (TDD, MapCanvas.test.tsx** — the file mocks maplibre with `MockMap`/`MockMarker` appending real marker DOM to `document.body`):

1. a place in `badgedPlaceIds` renders a `button.mc-pin-presence` inside its marker element with `aria-label` "Analyzed — view context"; a non-badged place doesn't;
2. clicking the badge calls `onBadgeClick(placeId)` and NOT `onMarkerClick`;
3. `fitTo={{ points: [{lat,lng},{lat,lng}], padding: {top:80,left:40,bottom:40,right:440} }}` calls the mock map's `fitBounds` with a bounds object covering the points and the exact padding (extend the maplibre mock with `fitBounds = vi.fn()` and, if the real code uses `maplibregl.LngLatBounds`, a minimal `LngLatBounds` stub — mirror how the mock currently stubs classes);
4. a single-point `fitTo` still calls `fitBounds` (degenerate bounds) with `maxZoom` capped.

- [ ] **Step 2: Implement.** New props:

```ts
badgedPlaceIds?: Set<string>;
onBadgeClick?: (placeId: string) => void;
fitTo?: { points: LatLng[]; padding: { top: number; right: number; bottom: number; left: number } } | null;
```

In the marker-build loop (after `el.innerHTML = iconHtml(...)`), append a real node when badged:

```ts
if (badgedPlaceIds?.has(place.id)) {
  const badge = document.createElement("button");
  badge.type = "button";
  badge.className = "mc-pin-presence";
  badge.setAttribute("aria-label", "Analyzed — view context");
  badge.addEventListener("click", (event) => {
    event.stopPropagation();
    onBadgeClickRef.current?.(place.id);
  });
  el.appendChild(badge);
}
```

(Add `onBadgeClickRef` mirroring `onMarkerClickRef` at `:171,182`; add `badgedPlaceIds` to the marker-rebuild effect's dependency array so badge presence updates rebuild markers — check what that effect currently keys on and match its idiom.)

`fitTo` consumption (new effect alongside the `flyTo` one at `:354-359`):

```ts
useEffect(() => {
  const map = mapRef.current;
  if (!map || !fitTo || fitTo.points.length === 0) return;
  const bounds = fitTo.points.reduce(
    (acc, p) => acc.extend([p.lng, p.lat]),
    new maplibregl.LngLatBounds([fitTo.points[0].lng, fitTo.points[0].lat], [fitTo.points[0].lng, fitTo.points[0].lat]),
  );
  map.fitBounds(bounds, { padding: fitTo.padding, maxZoom: 16, duration: 600 });
}, [fitTo]);
```

CSS (`mapWorkspace.css`, near `.mc-pin-badge`): `.mc-pin-presence{position:absolute;top:-4px;left:-4px;width:14px;height:14px;border-radius:50%;border:1.5px solid var(--surface);background:var(--text-dim);padding:0;cursor:pointer;}` — monochrome dot, no evaluative color. (Adjust offsets against the real `.mc-pin-badge` positioning so the two don't collide — read that rule first.)

- [ ] **Step 3: Pass + commit**: `feat(map): neutral presence badges + fitTo bounds with padding`

---

### Task 4: Badge tap → scroll to card; fit-on-analysis

**Files:** Modify `frontend/src/components/AssistantPanel.tsx` (+test), `frontend/src/components/MapWorkspace.tsx` (+test).

- [ ] **Step 1 (TDD, AssistantPanel):** new prop `focusCard?: AnalysisCardData | null`. Give each rendered `AnalysisCard` a wrapper `<div ref={...} data-card-index={index}>`; keep refs in a `useRef(new Map<number, HTMLDivElement>())` populated via callback refs. Effect: when `focusCard` changes and matches an item's `card` by object identity (newest match wins — iterate from the end), call `.scrollIntoView({ behavior: "smooth", block: "center" })` on its element. Test: jsdom lacks smooth scrolling — stub `Element.prototype.scrollIntoView = vi.fn()` and assert it fires on the right wrapper when `focusCard` is set, and does NOT fire when `focusCard` is null or unknown.

- [ ] **Step 2 (TDD, MapWorkspace):**
  - `const [focusCard, setFocusCard] = useState<AnalysisCardData | null>(null);`
  - `handleBadgeClick(placeId)`: find the NEWEST `analysis_card` item whose `card.placeIds.includes(placeId)` (reverse scan of `thread.items`); if found: `setRailView("tabby"); if (isMobile) setDrawerCollapsed(false); setFocusCard(found.card);`. (Also `setDrawerCollapsed(false)` on desktop if `drawer.collapsed` — a peeked drawer should open.)
  - Pass `onBadgeClick={handleBadgeClick}` and `badgedPlaceIds` to MapCanvas, `focusCard={focusCard}` to AssistantPanel.
  - **Fit-on-analysis:** `const [fitTo, setFitTo] = useState<MapCanvas's fitTo shape | null>(null);` In `applyAssistantToolResult`, when `effect.card` lands: resolve the card's placeIds against `data.places` (lat/lng non-null) and, if ≥1 point:

```ts
const points = effect.card.placeIds
  .map((id) => data.places.find((p) => p.id === id))
  .filter((p): p is Place => Boolean(p && p.latitude != null && p.longitude != null))
  .map((p) => ({ lat: p.latitude as number, lng: p.longitude as number }));
if (points.length > 0) {
  const rightInset = isMobile ? 40 : (drawer.collapsed ? DRAWER_PEEK : drawer.widthPx) + 40;
  const bottomInset = isMobile ? Math.round(window.innerHeight * 0.5) : 40;
  setFitTo({ points, padding: { top: 90, left: 40, right: rightInset, bottom: bottomInset } });
}
```

  - Pass `fitTo={fitTo}` to MapCanvas. Update the MapCanvas mock in MapWorkspace.test.tsx: add `badge-${place.id}` buttons wired to `onBadgeClick` (per the established `marker-${id}` convention) and capture `fitTo` like `flyToCaptures`.
  - Tests: (a) analyze flow → badge buttons appear for the analyzed place ids and `fitTo` captured with drawer-width-aware right padding; (b) badge tap → panel receives the newest matching card as `focusCard` (assert scrollIntoView stub fired) and the rail is the active view; (c) filter change via ContextStrip → badges cleared (no badge buttons); (d) deleting a place removes its badge but keeps others.

- [ ] **Step 3: Full suite + tsc + build green. Commit**: `feat(rail): badge taps focus the newest card; analyses fit the camera`

---

### Task 5: Gate + E2E + merge (coordinator)

- [ ] Full gate; E2E via `/verify` recipe: analyze → presence dot on pin + camera fits with the rail visible; tap dot → thread scrolls to card (sheet raises on a narrow viewport if practical to simulate via resize); change radius via strip → dot disappears; delete place → dot gone; invariant sweep (badge carries no verdict language). Fresh-context final review; squash-merge.

## Out of scope
- Verdict-text badges (explicitly deferred by the spec pending legend + comprehension work)
- Proactivity (Slice 5), sheet snap mechanics (Slice 6), tab deletion (Slice 7)
