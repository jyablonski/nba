import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SeasonSelect } from "@/components/season-select";

describe("SeasonSelect", () => {
  it("still changes season when rendered", () => {
    const setSeason = vi.fn();
    render(
      <SeasonSelect season="2025-26" seasons={["2025-26", "2024-25"]} setSeason={setSeason} />
    );
    const select = screen.getByLabelText("Season");
    expect(select).toHaveValue("2025-26");
    fireEvent.change(select, { target: { value: "2024-25" } });
    expect(setSeason).toHaveBeenCalledWith("2024-25");
  });
});
