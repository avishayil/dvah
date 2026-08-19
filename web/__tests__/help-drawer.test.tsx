import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const hintsIndex = vi.fn();
const hint = vi.fn();
const getSettings = vi.fn();

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message);
    }
  }
  return {
    ApiError,
    api: {
      hintsIndex: (...a: any[]) => hintsIndex(...a),
      hint: (...a: any[]) => hint(...a),
      walkthrough: vi.fn(),
      solution: vi.fn(),
      tutor: vi.fn(),
      getSettings: (...a: any[]) => getSettings(...a),
    },
  };
});

import { HelpDrawer } from "@/components/help-drawer";

describe("HelpDrawer", () => {
  beforeEach(() => {
    hintsIndex.mockReset();
    hint.mockReset();
    getSettings.mockReset();
    hintsIndex.mockResolvedValue({ invariant: "INV-06", count: 3, tiers: [] });
  });

  it("reveals hints one tier at a time", async () => {
    getSettings.mockResolvedValue({ tutor: { enabled: true }, model: { ready: true } });
    hint.mockResolvedValueOnce({ level: "nudge", text: "What trust level is that data?" });
    render(<HelpDrawer open onOpenChange={() => {}} challengeId="DVAH-003" sessionId="s1" />);
    fireEvent.click(screen.getByRole("button", { name: /reveal first hint/i }));
    await waitFor(() => expect(hint).toHaveBeenCalledWith("DVAH-003", 0, "s1"));
    expect(await screen.findByText(/what trust level is that data/i)).toBeInTheDocument();
  });

  it("hides the tutor input and points to Settings when the tutor isn't enabled", async () => {
    getSettings.mockResolvedValue({ tutor: { enabled: false }, model: { ready: false } });
    render(<HelpDrawer open onOpenChange={() => {}} challengeId="DVAH-003" sessionId="s1" />);
    expect(await screen.findByText(/isn.t enabled/i)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/ask for a nudge/i)).not.toBeInTheDocument();
  });

  it("shows the tutor input only when the tutor is ready", async () => {
    getSettings.mockResolvedValue({ tutor: { enabled: true }, model: { ready: true } });
    render(<HelpDrawer open onOpenChange={() => {}} challengeId="DVAH-003" sessionId="s1" />);
    expect(await screen.findByPlaceholderText(/ask for a nudge/i)).toBeInTheDocument();
  });
});
