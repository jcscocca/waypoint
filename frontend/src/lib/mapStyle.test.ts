import { describe, expect, it } from "vitest";
import {
  buildMapStyle,
  CIVIC_MAP_COLORS,
  cartoRasterStyle,
  fallbackMapStyle,
  TILES_URL,
} from "./mapStyle";

describe("buildMapStyle", () => {
  it("points the vector source at the self-hosted PMTiles file via the pmtiles protocol", () => {
    const style = buildMapStyle("light", "http://localhost:8000");
    const source = style.sources.protomaps as { type: string; url?: string };
    expect(source.type).toBe("vector");
    expect(source.url).toBe(`pmtiles://http://localhost:8000${TILES_URL}`);
  });

  it("self-hosts glyphs and sprites (no external hosts)", () => {
    const style = buildMapStyle("dark", "http://localhost:8000");
    expect(style.glyphs).toBe("http://localhost:8000/basemaps-assets/fonts/{fontstack}/{range}.pbf");
    expect(String(style.sprite)).toContain("http://localhost:8000/basemaps-assets/sprites/");
    const externals = JSON.stringify(style).match(/https?:\/\/(?!localhost:8000)[^"]+/g) ?? [];
    // Attribution links are the only allowed external URLs.
    for (const url of externals) {
      expect(url).toMatch(/openstreetmap\.org|protomaps\.com/);
    }
  });

  it("produces a non-empty basemap layer list for both themes", () => {
    expect(buildMapStyle("light", "http://x").layers.length).toBeGreaterThan(10);
    expect(buildMapStyle("dark", "http://x").layers.length).toBeGreaterThan(10);
  });

  it("credits OpenStreetMap in the source attribution", () => {
    const source = buildMapStyle("light", "http://x").sources.protomaps as { attribution?: string };
    expect(source.attribution).toContain("OpenStreetMap");
  });
});

describe("fallbackMapStyle", () => {
  it("is a background-only style using the pinned civic background color", () => {
    const style = fallbackMapStyle("light");
    expect(style.layers).toHaveLength(1);
    expect(style.layers[0].type).toBe("background");
    expect(JSON.stringify(style)).toContain(CIVIC_MAP_COLORS.light.background);
  });
});

describe("cartoRasterStyle", () => {
  it("keeps the temporary Carto raster fallback reachable behind the dev flag", () => {
    const style = cartoRasterStyle();
    const source = style.sources.carto as { type: string; tiles?: string[] };
    expect(source.type).toBe("raster");
    expect(source.tiles?.[0]).toContain("basemaps.cartocdn.com");
  });
});
