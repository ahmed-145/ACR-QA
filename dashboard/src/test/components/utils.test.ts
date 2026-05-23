import { describe, it, expect } from "vitest";
import { cn, severityColor, riskColor, formatDate, truncate } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("handles conditional classes", () => {
    const flag = false as boolean;
    expect(cn("base", flag && "nope", "yes")).toBe("base yes");
  });

  it("resolves tailwind conflicts (last wins)", () => {
    const result = cn("text-red-500", "text-blue-500");
    expect(result).toContain("text-blue-500");
    expect(result).not.toContain("text-red-500");
  });
});

describe("severityColor", () => {
  it("returns red class for HIGH", () => {
    expect(severityColor("HIGH")).toContain("red");
  });

  it("returns amber/yellow class for MEDIUM", () => {
    const cls = severityColor("MEDIUM");
    expect(cls.includes("amber") || cls.includes("yellow")).toBe(true);
  });

  it("returns blue/sky class for LOW", () => {
    const cls = severityColor("LOW");
    expect(cls.includes("blue") || cls.includes("sky")).toBe(true);
  });

  it("returns gray for unknown severity", () => {
    expect(severityColor("UNKNOWN")).toContain("gray");
  });
});

describe("riskColor", () => {
  it("returns red class for high", () => {
    expect(riskColor("high")).toContain("red");
  });

  it("returns yellow/amber class for medium", () => {
    const cls = riskColor("medium");
    expect(cls.includes("amber") || cls.includes("yellow")).toBe(true);
  });

  it("returns green class for low", () => {
    expect(riskColor("low")).toContain("green");
  });
});

describe("truncate", () => {
  it("returns string unchanged when short enough", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates and appends ellipsis", () => {
    const result = truncate("hello world", 5);
    expect(result).toBe("hello…");
  });

  it("handles empty string", () => {
    expect(truncate("", 5)).toBe("");
  });
});

describe("formatDate", () => {
  it("returns a non-empty string for a valid ISO date", () => {
    const result = formatDate("2024-01-15T10:00:00Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("returns fallback for invalid date", () => {
    const result = formatDate("not-a-date");
    expect(typeof result).toBe("string");
  });
});
