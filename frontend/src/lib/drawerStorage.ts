import type { DrawerState, SheetSnap } from "../types";
import { clampWidth, DRAWER_DEFAULT, SHEET_SNAPS } from "./drawer";

const WIDTH_KEY = "compcat.drawer.width";
const COLLAPSED_KEY = "compcat.drawer.collapsed";
const SNAP_KEY = "compcat.drawer.snap";

function parseSnap(raw: string | null): SheetSnap {
  return SHEET_SNAPS.includes(raw as SheetSnap) ? (raw as SheetSnap) : "half";
}

export function loadDrawerState(): DrawerState {
  try {
    const rawWidth = localStorage.getItem(WIDTH_KEY);
    const rawCollapsed = localStorage.getItem(COLLAPSED_KEY);
    const widthPx = rawWidth === null ? DRAWER_DEFAULT : clampWidth(Number(rawWidth));
    const collapsed = rawCollapsed === "true";
    const snap = parseSnap(localStorage.getItem(SNAP_KEY));
    // Reconcile the collapsed⇔bar invariant for stores written before snap existed.
    return { collapsed, widthPx, snap: collapsed ? "bar" : snap === "bar" ? "half" : snap };
  } catch {
    return { collapsed: false, widthPx: DRAWER_DEFAULT, snap: "half" };
  }
}

export function saveDrawerState(state: DrawerState): void {
  try {
    localStorage.setItem(WIDTH_KEY, String(state.widthPx));
    localStorage.setItem(COLLAPSED_KEY, String(state.collapsed));
    localStorage.setItem(SNAP_KEY, state.snap);
  } catch {
    // ignore: private mode or disabled storage degrades to in-memory defaults
  }
}
