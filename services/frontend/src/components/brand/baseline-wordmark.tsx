export function BaselineWordmark({ className }: { className?: string }) {
  return (
    // The lockup is a static SVG. Empty alt: the parent link is named "Baseline".
    // eslint-disable-next-line @next/next/no-img-element -- SVG lockup from /public/logo
    <img
      src="/logo/baseline-lockup.svg"
      alt=""
      width={198}
      height={59}
      className={className}
      draggable={false}
    />
  );
}
