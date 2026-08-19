import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const drive = vi.fn();
vi.mock("driver.js", () => ({ driver: () => ({ drive }) }));

import { Tour } from "@/components/tour";

describe("Tour", () => {
  beforeEach(() => {
    // jsdom in this env exposes no localStorage; provide an in-memory stub.
    const store = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (k: string) => store.get(k) ?? null,
        setItem: (k: string, v: string) => void store.set(k, v),
        removeItem: (k: string) => void store.delete(k),
        clear: () => store.clear(),
      },
    });
    drive.mockClear();
  });

  it("renders a replay button and marks first-run seen once anchors mount", async () => {
    // The step target must be present for the first-run tour to launch; the tour now
    // waits for it and only marks itself seen once it actually starts.
    document.body.innerHTML = '<div data-tour="x"></div>';
    render(<Tour tourKey="t1" steps={[{ el: '[data-tour="x"]', title: "a", text: "b" }]} />);
    expect(screen.getByRole("button", { name: /take the guided tour/i })).toBeInTheDocument();
    await waitFor(() =>
      expect(window.localStorage.getItem("dvah:tour:t1:v1")).toBe("seen"),
    );
    expect(drive).toHaveBeenCalled();
  });

  it("does not launch the driver when no target elements are present", () => {
    render(<Tour tourKey="t2" steps={[{ el: '[data-tour="none"]', title: "a", text: "b" }]} />);
    fireEvent.click(screen.getByRole("button", { name: /take the guided tour/i }));
    expect(drive).not.toHaveBeenCalled();
  });
});
