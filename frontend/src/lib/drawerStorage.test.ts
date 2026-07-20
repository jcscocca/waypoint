// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { DRAWER_DEFAULT } from "./drawer";
import { loadDrawerState, saveDrawerState } from "./drawerStorage";

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("drawer storage", () => {
  it("defaults to an open drawer at the default width and the half snap when nothing is stored", () => {
    expect(loadDrawerState()).toEqual({ collapsed: false, widthPx: DRAWER_DEFAULT, snap: "half" });
  });

  it("round-trips a saved state, clamping the width and preserving the snap", () => {
    // collapsed:false + snap:"full" is an invariant-consistent pair (collapsed ⇔ bar).
    saveDrawerState({ collapsed: false, widthPx: 99999, snap: "full" });
    const loaded = loadDrawerState();
    expect(loaded.collapsed).toBe(false);
    // jsdom window.innerWidth defaults to 1024, so drawerMax() == min(1024-96, 1024*0.9) == 922
    expect(loaded.widthPx).toBe(922);
    expect(loaded.snap).toBe("full");
  });

  it("falls back to the half snap when the stored snap is unknown", () => {
    localStorage.setItem("compcat.drawer.snap", "sideways");
    expect(loadDrawerState().snap).toBe("half");
  });

  it("falls back to the half snap when the snap key is absent", () => {
    saveDrawerState({ collapsed: false, widthPx: DRAWER_DEFAULT, snap: "full" });
    localStorage.removeItem("compcat.drawer.snap");
    expect(loadDrawerState().snap).toBe("half");
  });

  it("falls back to defaults when storage throws", () => {
    const getItem = vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(loadDrawerState()).toEqual({ collapsed: false, widthPx: DRAWER_DEFAULT, snap: "half" });
    expect(getItem).toHaveBeenCalled();
  });
});

it("reconciles pre-snap stores to the collapsed⇔bar invariant", () => {
  localStorage.setItem("compcat.drawer.collapsed", "true");
  localStorage.removeItem("compcat.drawer.snap");
  expect(loadDrawerState()).toMatchObject({ collapsed: true, snap: "bar" });
  localStorage.setItem("compcat.drawer.collapsed", "false");
  localStorage.setItem("compcat.drawer.snap", "bar");
  expect(loadDrawerState()).toMatchObject({ collapsed: false, snap: "half" });
});
