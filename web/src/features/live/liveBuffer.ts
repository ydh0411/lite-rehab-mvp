export function appendBounded<T>(items: readonly T[], item: T, limit: number): T[] {
  if (limit <= 0) {
    throw new Error("limit must be positive")
  }
  return [...items, item].slice(-limit)
}
