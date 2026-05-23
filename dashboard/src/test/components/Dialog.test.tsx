import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Dialog } from "@/components/ui/dialog";

describe("Dialog", () => {
  it("renders nothing when closed", () => {
    render(<Dialog open={false} onClose={vi.fn()}>Hidden</Dialog>);
    expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
  });

  it("renders children when open", () => {
    render(<Dialog open={true} onClose={vi.fn()}>Visible</Dialog>);
    expect(screen.getByText("Visible")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(<Dialog open={true} onClose={vi.fn()} title="My Dialog">Body</Dialog>);
    expect(screen.getByText("My Dialog")).toBeInTheDocument();
  });

  it("calls onClose when backdrop clicked", () => {
    const onClose = vi.fn();
    render(<Dialog open={true} onClose={onClose}>Body</Dialog>);
    const backdrop = document.querySelector("[data-testid='dialog-backdrop']");
    fireEvent.click(backdrop!);
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when X button clicked", () => {
    const onClose = vi.fn();
    render(<Dialog open={true} onClose={onClose} title="Close Me">Body</Dialog>);
    const xBtn = document.querySelector("button.modal-close");
    fireEvent.click(xBtn!);
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn();
    render(<Dialog open={true} onClose={onClose}>Body</Dialog>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
