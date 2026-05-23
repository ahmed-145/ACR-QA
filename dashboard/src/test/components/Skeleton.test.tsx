import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Skeleton, SkeletonCard, SkeletonTable } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/ui/error-boundary";

describe("Skeleton", () => {
  it("renders with animate-pulse class", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("animate-pulse");
  });

  it("merges custom className", () => {
    const { container } = render(<Skeleton className="h-10 w-full" />);
    expect(container.firstChild).toHaveClass("h-10", "w-full");
  });
});

describe("SkeletonCard", () => {
  it("renders 3 skeleton lines", () => {
    const { container } = render(<SkeletonCard />);
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBe(3);
  });
});

describe("SkeletonTable", () => {
  it("renders header + default 5 rows", () => {
    const { container } = render(<SkeletonTable />);
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBe(6); // 1 header + 5 rows
  });

  it("respects custom rows prop", () => {
    const { container } = render(<SkeletonTable rows={3} />);
    const pulses = container.querySelectorAll(".animate-pulse");
    expect(pulses.length).toBe(4); // 1 header + 3 rows
  });
});

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <span>OK</span>
      </ErrorBoundary>
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("renders fallback on error", () => {
    const Bomb = () => { throw new Error("boom"); };
    const { container } = render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    );
    expect(container.querySelector("[role='alert']")).not.toBeNull();
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("has a Try again button in error state", () => {
    const Bomb = () => { throw new Error("boom"); };
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    );
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
