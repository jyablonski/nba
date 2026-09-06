import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const queryNlp = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/ask",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams("season=2025-26"),
}));

vi.mock("@/lib/api", () => ({
  api: {
    listSeasons: async () => ({
      data: [{ season: "2025-26" }],
      meta: { total: 1, limit: 1, offset: 0 },
    }),
    queryNlp: (...args: unknown[]) => queryNlp(...args),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import AskPage from "@/app/ask/page";
import { Providers } from "@/components/providers";

function renderPage() {
  return render(
    <Providers>
      <AskPage />
    </Providers>
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("ask page", () => {
  beforeEach(() => {
    queryNlp.mockReset();
  });

  it("shows an empty state before the first ask", () => {
    renderPage();
    expect(screen.getByText("Nothing asked yet")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Try" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask a bounded question")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("replaces the previous Q&A with the latest submit", async () => {
    queryNlp
      .mockResolvedValueOnce({
        answer: "Stephen Curry remaining salary is $55,761,217.",
        data: [{ player: "Stephen Curry", remaining_salary: 55761217 }],
      })
      .mockResolvedValueOnce({
        answer: "Golden State Warriors remaining payroll is $210,000,000.",
        data: [{ team: "Golden State Warriors", remaining_payroll: 210000000 }],
      });

    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /Curry's salary/i }));
    await waitFor(() => {
      expect(
        screen.getByText("Stephen Curry remaining salary is $55,761,217.")
      ).toBeInTheDocument();
    });
    const first = screen.getByRole("article", { name: "Latest question and answer" });
    expect(within(first).getByText("What is Curry's salary?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in Players →" })).toHaveAttribute(
      "href",
      "/players"
    );
    expect(within(first).getByText("Stephen Curry")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Warriors payroll/i }));
    await waitFor(() => {
      expect(
        screen.getByText("Golden State Warriors remaining payroll is $210,000,000.")
      ).toBeInTheDocument();
    });

    const latest = screen.getByRole("article", { name: "Latest question and answer" });
    expect(within(latest).queryByText("What is Curry's salary?")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Stephen Curry remaining salary is $55,761,217.")
    ).not.toBeInTheDocument();
    expect(within(latest).getByText("What is the Warriors payroll?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in Teams →" })).toHaveAttribute("href", "/teams");
    expect(queryNlp).toHaveBeenCalledTimes(2);
    expect(queryNlp).toHaveBeenNthCalledWith(1, "What is Curry's salary?", "2025-26");
    expect(queryNlp).toHaveBeenNthCalledWith(2, "What is the Warriors payroll?", "2025-26");
  });

  it("clears the previous answer and shows loading on the current slot", async () => {
    queryNlp.mockResolvedValueOnce({
      answer: "Kawhi Leonard has 12 back-to-back sets",
      data: [],
    });
    const second = deferred<{ answer: string; data: never[] }>();
    queryNlp.mockReturnValueOnce(second.promise);

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /back-to-backs has Kawhi/i }));
    await waitFor(() => {
      expect(screen.getByText("Kawhi Leonard has 12 back-to-back sets")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /leads the West/i }));
    await waitFor(() => {
      expect(screen.queryByText("Kawhi Leonard has 12 back-to-back sets")).not.toBeInTheDocument();
      expect(screen.getByRole("status", { name: "Asking…" })).toBeInTheDocument();
    });
    expect(
      within(screen.getByRole("article", { name: "Latest question and answer" })).getByText(
        "Who leads the West?"
      )
    ).toBeInTheDocument();

    second.resolve({ answer: "Oklahoma City is first in the West.", data: [] });
    await waitFor(() => {
      expect(screen.getByText("Oklahoma City is first in the West.")).toBeInTheDocument();
    });
    expect(screen.queryByRole("status", { name: "Asking…" })).not.toBeInTheDocument();
  });

  it("submits the typed question and shows an API error on the current slot", async () => {
    queryNlp.mockRejectedValueOnce(new Error("Unable to load data. Try again in a moment."));

    renderPage();
    fireEvent.change(screen.getByPlaceholderText("Ask a bounded question"), {
      target: { value: "Who leads the East?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to load data. Try again in a moment.")).toBeInTheDocument();
    });
    expect(
      within(screen.getByRole("article", { name: "Latest question and answer" })).getByText(
        "Who leads the East?"
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Couldn't load an answer.")).toBeInTheDocument();
    expect(screen.queryByText("Nothing asked yet")).not.toBeInTheDocument();
  });
});
