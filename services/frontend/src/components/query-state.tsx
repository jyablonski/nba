export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="space-y-2 py-4" role="status" aria-label={label}>
      <div className="h-[9px] w-[96%] animate-pulse bg-skel-1" />
      <div className="h-[9px] w-full animate-pulse bg-skel-2" />
      <div className="h-[9px] w-[88%] animate-pulse bg-skel-1" />
      <div className="h-[9px] w-[92%] animate-pulse bg-skel-2" />
      <p className="pt-1 text-sm text-ink-3">{label}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="px-3 py-10 text-center">
      <p className="font-medium text-destructive">{message}</p>
    </div>
  );
}

export function EmptyState({
  title = "No data yet",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <p className="font-medium">{title}</p>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
