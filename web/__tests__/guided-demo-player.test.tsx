import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GuidedDemoPlayer, type DemoFrame } from "@/components/guided-demo-player";

const FRAMES: DemoFrame[] = [
  { image: "01-workspace.png", caption: "This is DVAH-001, the agent harness.", cursor: { xPct: 80, yPct: 40 }, focus: { xPct: 20, yPct: 5, wPct: 50, hPct: 60 }, click: true, dwellMs: 3000 },
  { image: "02-exploit-red.png", caption: "The exploit runs and the board goes red.", cursor: { xPct: 70, yPct: 30 }, focus: { xPct: 60, yPct: 5, wPct: 35, hPct: 70 }, click: true, dwellMs: 3000 },
  { image: "05-green.png", caption: "Proven: the board is green.", cursor: null, focus: { xPct: 60, yPct: 5, wPct: 35, hPct: 80 }, click: false, dwellMs: 4000 },
];

beforeEach(() => {
  // jsdom lacks matchMedia; mock as reduced-motion so autoplay is off (deterministic stepping).
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
});

describe("GuidedDemoPlayer", () => {
  it("renders the first frame + caption + cursor", () => {
    render(<GuidedDemoPlayer frames={FRAMES} />);
    expect(screen.getByTestId("demo-caption")).toHaveTextContent("1/3");
    expect(screen.getByTestId("demo-caption")).toHaveTextContent(/agent harness/i);
    expect(screen.getByTestId("demo-cursor")).toBeInTheDocument();
  });

  it("zooms into the focus region (transform with scale > 1)", () => {
    render(<GuidedDemoPlayer frames={FRAMES} />);
    const zoom = screen.getByTestId("demo-zoom");
    // frame 1 has a focus rect → a scale() transform is applied.
    expect(zoom.style.transform).toMatch(/scale\(/);
    expect(zoom.style.transform).not.toBe("none");
  });

  it("opens on the full frame (phase=full, no zoom) when motion is allowed", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false, // motion allowed → autoplay begins on the full-frame beat
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    render(<GuidedDemoPlayer frames={FRAMES} />);
    const zoom = screen.getByTestId("demo-zoom");
    expect(zoom.getAttribute("data-phase")).toBe("full");
    expect(zoom.style.transform).toBe("none"); // beat 1: whole frame, un-zoomed
    expect(screen.queryByTestId("demo-cursor")).not.toBeInTheDocument(); // cursor waits for the click beat
  });

  it("advances steps and exposes the Open DVAH-001 link on the last frame", () => {
    render(<GuidedDemoPlayer frames={FRAMES} />);
    fireEvent.click(screen.getByRole("button", { name: /next step/i }));
    expect(screen.getByTestId("demo-caption")).toHaveTextContent(/board goes red/i);

    fireEvent.click(screen.getByRole("button", { name: /next step/i }));
    expect(screen.getByTestId("demo-caption")).toHaveTextContent("3/3");
    // last frame: no cursor, and the jump-into-lab CTA appears.
    expect(screen.queryByTestId("demo-cursor")).not.toBeInTheDocument();
    const open = screen.getByTestId("open-dvah-001");
    expect(open).toHaveAttribute("href", expect.stringContaining("/labs/DVAH-001-plan-time-authorization"));
  });
});
