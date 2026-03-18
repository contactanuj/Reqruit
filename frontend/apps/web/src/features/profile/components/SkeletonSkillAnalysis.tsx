// SkeletonSkillAnalysis.tsx — FE-4.6: Skeleton for skill analysis (UX-14)

const shimmer =
  "animate-pulse bg-gradient-to-r from-zinc-800 via-zinc-700 to-zinc-800 rounded";

export function SkeletonSkillAnalysis() {
  return (
    <div className="flex flex-col gap-6" aria-label="Loading skill analysis…" aria-busy="true">
      {/* Your Skills section skeleton */}
      <div className="flex flex-col gap-3">
        <div className={`${shimmer} h-5 w-1/4`} />
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex flex-col gap-1.5">
            <div className="flex justify-between">
              <div className={`${shimmer} h-4 w-1/5`} />
              <div className={`${shimmer} h-4 w-8`} />
            </div>
            <div className={`${shimmer} h-2 w-full`} />
          </div>
        ))}
      </div>

      {/* Trending section skeleton */}
      <div className="flex flex-col gap-3">
        <div className={`${shimmer} h-5 w-1/3`} />
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className={`${shimmer} h-6 w-20`} />
          ))}
        </div>
      </div>

      {/* Skill Gaps section skeleton */}
      <div className="flex flex-col gap-3">
        <div className={`${shimmer} h-5 w-1/4`} />
        {[1, 2].map((i) => (
          <div key={i} className={`${shimmer} h-8 w-full`} />
        ))}
      </div>
    </div>
  );
}
