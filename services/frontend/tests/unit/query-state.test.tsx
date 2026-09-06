import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState, ErrorState, LoadingState } from "@/components/query-state";

describe("query states", () => {
  it("renders loading, error, and empty copy", () => {
    const { rerender } = render(<LoadingState label="Fetching…" />);
    expect(screen.getByText("Fetching…")).toBeInTheDocument();

    rerender(<ErrorState message="API is down" />);
    expect(screen.getByText("API is down")).toBeInTheDocument();

    rerender(<EmptyState message="Nothing here" />);
    expect(screen.getByText("No data yet")).toBeInTheDocument();
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });
});
