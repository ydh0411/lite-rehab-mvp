type EcgTraceProps = {
  connected: boolean
  samples: readonly number[]
}


function tracePoints(samples: readonly number[]): string {
  if (samples.length < 2) {
    return "0,45 600,45"
  }
  const minimum = Math.min(...samples)
  const maximum = Math.max(...samples)
  const span = Math.max(1, maximum - minimum)
  return samples
    .map((sample, index) => {
      const x = (index / (samples.length - 1)) * 600
      const y = 76 - ((sample - minimum) / span) * 62
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
}


export function EcgTrace({ connected, samples }: EcgTraceProps) {
  return (
    <svg
      className={`ecg-trace${connected ? " connected" : ""}`}
      viewBox="0 0 600 90"
      role="img"
      aria-label={connected ? "Live ECG waveform" : "ECG leads off"}
      preserveAspectRatio="none"
    >
      <defs>
        <pattern id="ecg-grid-small" width="12" height="12" patternUnits="userSpaceOnUse">
          <path d="M 12 0 L 0 0 0 12" fill="none" stroke="currentColor" strokeWidth="0.45" />
        </pattern>
        <pattern id="ecg-grid-large" width="60" height="60" patternUnits="userSpaceOnUse">
          <rect width="60" height="60" fill="url(#ecg-grid-small)" />
          <path d="M 60 0 L 0 0 0 60" fill="none" stroke="currentColor" strokeWidth="0.8" />
        </pattern>
      </defs>
      <rect width="600" height="90" fill="url(#ecg-grid-large)" className="ecg-grid" />
      <polyline
        points={connected ? tracePoints(samples) : "0,45 600,45"}
        fill="none"
        className="ecg-line"
        strokeWidth={connected ? 2 : 1.25}
        strokeDasharray={connected ? undefined : "6 7"}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
