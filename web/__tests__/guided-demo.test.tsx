import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { GuidedDemoRunner, type DemoStep } from "@/components/guided-demo";

describe("GuidedDemoRunner", () => {
  it("shows the intro caption and runs each forward step action in order (incl. the patch)", async () => {
    const calls: string[] = [];
    const steps: DemoStep[] = [
      { caption: "intro caption" },
      { caption: "run the exploit", run: async () => void calls.push("exploit") },
      { caption: "why it happened" },
      { caption: "apply the fix", run: async () => void calls.push("patch") },
      { caption: "prove it", run: async () => void calls.push("prove") },
      { caption: "done" },
    ];
    // auto=false → no timers; we drive with Next so the assertions are deterministic.
    render(<GuidedDemoRunner steps={steps} onClose={() => {}} auto={false} />);
    expect(screen.getByTestId("guided-demo-caption").textContent).toBe("intro caption");

    const clickNext = async () =>
      userEvent.click(await screen.findByRole("button", { name: /next step/i }));

    await clickNext(); // → exploit
    await waitFor(() => expect(calls).toEqual(["exploit"]));
    await clickNext(); // → why (no action)
    await clickNext(); // → patch
    await waitFor(() => expect(calls).toEqual(["exploit", "patch"]));
    await clickNext(); // → prove
    await waitFor(() => expect(calls).toEqual(["exploit", "patch", "prove"]));
    expect(screen.getByTestId("guided-demo-caption").textContent).toBe("prove it");

    // Reaching the last step swaps Next for a finish button.
    await clickNext();
    expect(screen.getByRole("button", { name: /finish the demo/i })).toBeTruthy();
  });

  it("calls onClose from the finish button", async () => {
    const onClose = vi.fn();
    const steps: DemoStep[] = [{ caption: "only step" }];
    render(<GuidedDemoRunner steps={steps} onClose={onClose} auto={false} />);
    await userEvent.click(screen.getByRole("button", { name: /finish the demo/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
