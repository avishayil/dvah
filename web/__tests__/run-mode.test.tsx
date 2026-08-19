import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

const getSettings = vi.fn();
vi.mock("@/lib/api", () => ({
  api: { getSettings: (...a: unknown[]) => getSettings(...a) },
}));

import { RunModeBadge } from "@/components/run-mode";

describe("RunModeBadge (reflects the single global run mode)", () => {
  beforeEach(() => getSettings.mockReset());

  it("shows Deterministic and no live button by default", async () => {
    getSettings.mockResolvedValue({ run_mode: "deterministic", model: { key_set: false }, env_keys: {} });
    render(<RunModeBadge onLiveRun={vi.fn()} />);
    await waitFor(() => expect(getSettings).toHaveBeenCalled());
    const group = await screen.findByTestId("run-mode");
    expect(group.getAttribute("data-mode")).toBe("deterministic");
    expect(screen.getByText("Deterministic")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /run with live model/i })).toBeNull();
    // there's always a "change in Settings" link
    expect(screen.getByTestId("run-mode-settings-link")).toBeTruthy();
  });

  it("live mode with a key shows an actionable live-run button", async () => {
    getSettings.mockResolvedValue({ run_mode: "live", model: { key_set: true }, env_keys: {} });
    const onLiveRun = vi.fn();
    render(<RunModeBadge onLiveRun={onLiveRun} />);
    const btn = await screen.findByRole("button", { name: /run with live model/i });
    await userEvent.click(btn);
    expect(onLiveRun).toHaveBeenCalledTimes(1);
  });

  it("live mode without a key prompts to set one in Settings, no button", async () => {
    getSettings.mockResolvedValue({ run_mode: "live", model: { key_set: false }, env_keys: {} });
    render(<RunModeBadge onLiveRun={vi.fn()} />);
    await screen.findByTestId("run-mode");
    expect(screen.queryByRole("button", { name: /run with live model/i })).toBeNull();
    expect(screen.getByText(/set a model key/i)).toBeTruthy();
  });
});
