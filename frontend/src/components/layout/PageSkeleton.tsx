export function PageSkeleton() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-8 w-64 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-4 w-96 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>

      {/* Tabs skeleton */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700 pb-2">
        <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>

      {/* Content cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-xl" />
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-xl" />
      </div>

      <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-xl" />

      <div className="grid grid-cols-3 gap-4">
        <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    </div>
  );
}
