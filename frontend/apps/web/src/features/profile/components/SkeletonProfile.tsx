// SkeletonProfile.tsx — FE-4.3: Skeleton loading state for profile (UX-14)

const shimmer =
  "animate-pulse bg-gradient-to-r from-zinc-800 via-zinc-700 to-zinc-800 rounded";

function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`${shimmer} h-4 ${className}`} />;
}

export function SkeletonProfile() {
  return (
    <div className="flex flex-col gap-8" aria-label="Loading profile…" aria-busy="true">
      {/* Contact skeleton */}
      <div className="flex flex-col gap-3">
        <SkeletonLine className="w-1/3 h-6" />
        <SkeletonLine className="w-1/4" />
        <SkeletonLine className="w-1/5" />
      </div>

      {/* Summary skeleton */}
      <div className="flex flex-col gap-2">
        <SkeletonLine className="w-1/4 h-5" />
        <SkeletonLine className="w-full" />
        <SkeletonLine className="w-5/6" />
      </div>

      {/* Experience skeleton */}
      <div className="flex flex-col gap-3">
        <SkeletonLine className="w-1/4 h-5" />
        {[1, 2].map((i) => (
          <div key={i} className="flex flex-col gap-2 pl-4 border-l-2 border-border">
            <SkeletonLine className="w-1/3" />
            <SkeletonLine className="w-1/4" />
            <SkeletonLine className="w-full" />
          </div>
        ))}
      </div>

      {/* Skills skeleton */}
      <div className="flex flex-col gap-3">
        <SkeletonLine className="w-1/4 h-5" />
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className={`${shimmer} h-6 w-16`} />
          ))}
        </div>
      </div>
    </div>
  );
}
