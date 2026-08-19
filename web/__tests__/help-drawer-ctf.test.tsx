import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HelpDrawer } from "@/components/help-drawer";

// The drawer only calls the API from interaction handlers, not on render, so a
// minimal mock is enough for the CTF-locked rendering test.
vi.mock("@/lib/api", () => ({
  api: {
    getSettings: () => Promise.resolve({ tutor: { enabled: false }, model: { ready: false } }),
  },
  ApiError: class extends Error {},
}));

describe("HelpDrawer — CTF mode", () => {
  it("locks hints and the solution, keeps the walkthrough", () => {
    render(
      <HelpDrawer
        open
        onOpenChange={() => {}}
        challengeId="DVAH-001"
        sessionId="s1"
        mode="ctf"
      />,
    );
    expect(screen.getByText(/Hints are locked in CTF mode/i)).toBeInTheDocument();
    expect(screen.getByText(/solution is locked in CTF mode/i)).toBeInTheDocument();
    expect(screen.queryByText(/Reveal first hint/i)).not.toBeInTheDocument();
    // walkthrough remains available
    expect(screen.getByText(/Show walkthrough/i)).toBeInTheDocument();
  });
});
