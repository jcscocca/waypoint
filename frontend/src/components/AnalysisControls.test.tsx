import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisControls } from "./AnalysisControls";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("AnalysisControls", () => {
  it("defaults the analysis window to the current year through today", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-24T12:00:00-07:00"));

    render(
      <AnalysisControls
        selectedCount={0}
        onAnalyze={vi.fn()}
        onCompare={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Start date")).toHaveValue("2026-01-01");
    expect(screen.getByLabelText("End date")).toHaveValue("2026-06-24");
  });
});
