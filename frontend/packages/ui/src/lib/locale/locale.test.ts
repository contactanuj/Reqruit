import { describe, it, expect } from "vitest";
import { formatLPA, formatCTC, formatDate, formatNumber } from "./index";

describe("formatLPA", () => {
  it("formats 12 lakhs for IN locale", () => {
    expect(formatLPA(1_200_000, "IN")).toBe("₹12L");
  });

  it("formats 1.5 crore for IN locale", () => {
    expect(formatLPA(15_000_000, "IN")).toBe("₹1.5Cr");
  });

  it("formats 180K for US locale", () => {
    expect(formatLPA(180_000, "US")).toBe("$180K");
  });

  it("formats 1.2M for US locale", () => {
    expect(formatLPA(1_200_000, "US")).toBe("$1.2M");
  });

  it("formats 0 amount for IN locale", () => {
    expect(formatLPA(0, "IN")).toBe("₹0L");
  });
});

describe("formatCTC", () => {
  it("formats 25 lakhs p.a. for IN locale", () => {
    expect(formatCTC(2_500_000, "IN")).toBe("₹25L p.a.");
  });

  it("formats 180K/yr for US locale", () => {
    expect(formatCTC(180_000, "US")).toBe("$180K/yr");
  });
});

describe("formatDate", () => {
  it("formats date as DD/MM/YYYY for IN locale", () => {
    const date = new Date(2024, 0, 15); // Jan 15 2024
    expect(formatDate(date, "IN")).toBe("15/01/2024");
  });

  it("formats date as MM/DD/YYYY for US locale", () => {
    const date = new Date(2024, 0, 15);
    expect(formatDate(date, "US")).toBe("01/15/2024");
  });

  it("accepts ISO string", () => {
    expect(formatDate("2024-03-15", "IN")).toBe("15/03/2024");
  });

  it("accepts ISO string for US locale without timezone shift", () => {
    expect(formatDate("2024-03-15", "US")).toBe("03/15/2024");
  });
});

describe("formatNumber", () => {
  it("formats using Indian numbering system", () => {
    expect(formatNumber(1_500_000, "IN")).toBe("15,00,000");
  });

  it("formats using Western numbering system", () => {
    expect(formatNumber(1_500_000, "US")).toBe("1,500,000");
  });
});
