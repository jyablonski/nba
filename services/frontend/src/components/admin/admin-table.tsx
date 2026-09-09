import { Table } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/**
 * The shared TableCell/TableHead primitives ship with `px-0` on purpose — each
 * consumer supplies its own rhythm. Without it adjacent columns render flush
 * against each other ("Since successLast run"), so admin tables get their
 * spacing here once instead of on every cell.
 */
export function AdminTable({ className, ...props }: React.ComponentProps<typeof Table>) {
  return (
    <Table
      className={cn(
        "[&_td]:px-3 [&_th]:px-3",
        "[&_td:first-child]:pl-0 [&_th:first-child]:pl-0",
        "[&_td:last-child]:pr-0 [&_th:last-child]:pr-0",
        className
      )}
      {...props}
    />
  );
}
