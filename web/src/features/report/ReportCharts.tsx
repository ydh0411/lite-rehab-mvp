import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { SeriesPoint } from "../../app/api"


type TrendChartProps = {
  title: string
  description: string
  data: readonly SeriesPoint[]
  unit: string
  color?: string
}


export function TrendChart({ title, description, data, unit, color = "#087f7b" }: TrendChartProps) {
  return (
    <article className="report-chart-card">
      <header><strong>{title}</strong><span>{description}</span></header>
      {data.length ? (
        <div className="report-chart" aria-label={title}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={[...data]} margin={{ top: 8, right: 14, bottom: 0, left: -12 }}>
              <CartesianGrid stroke="#e4ebef" vertical={false} />
              <XAxis dataKey="t_s" tick={{ fill: "#6b7d88", fontSize: 11 }} tickLine={false} axisLine={false} unit="s" />
              <YAxis tick={{ fill: "#6b7d88", fontSize: 11 }} tickLine={false} axisLine={false} unit={unit} />
              <Tooltip
                contentStyle={{ border: "1px solid #d7e1e7", borderRadius: 7, fontSize: 12 }}
                formatter={(value) => [`${Number(value).toFixed(1)}${unit}`, title]}
                labelFormatter={(value) => `${value}s`}
              />
              <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="chart-empty">Not enough valid data for this chart.</div>
      )}
    </article>
  )
}
