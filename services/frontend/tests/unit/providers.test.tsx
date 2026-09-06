import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";

describe("providers", () => {
  it("renders children", () => {
    const { getByText } = render(
      <Providers>
        <p>ready</p>
      </Providers>
    );
    expect(getByText("ready")).toBeTruthy();
  });
});
