import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface DonutChartDatum {
  label: string;
  value: number;
  color: string;
}

const EMPTY_DATUM: DonutChartDatum[] = [
  { label: "None", value: 1, color: "var(--color-border)" },
];

export interface DonutChartProps {
  data: DonutChartDatum[];
  total: number;
  size?: number;
}

/** A tinted ring, animated on mount, with the total in its center. Falls
 * back to a flat grey ring when there's nothing to show yet, rather than
 * an empty/broken-looking chart. */
export function DonutChart({ data, total, size = 176 }: DonutChartProps) {
  const hasData = total > 0;
  const chartData = hasData ? data : EMPTY_DATUM;

  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="label"
            innerRadius="72%"
            outerRadius="100%"
            paddingAngle={hasData ? 3 : 0}
            isAnimationActive
            animationDuration={800}
            animationEasing="ease-out"
          >
            {chartData.map((d) => (
              <Cell
                key={d.label}
                fill={d.color}
                stroke="var(--color-surface)"
                strokeWidth={2}
              />
            ))}
          </Pie>
          {hasData && (
            <Tooltip
              formatter={(v, n) => [v, n]}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--color-border)",
                fontSize: 13,
              }}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-page font-semibold text-ink">{total}</span>
        <span className="text-helper text-muted">Total</span>
      </div>
    </div>
  );
}

export function DonutLegend({ data }: { data: DonutChartDatum[] }) {
  const nonZero = data.filter((d) => d.value > 0);
  if (nonZero.length === 0) {
    return <p className="text-helper text-muted">No data yet</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {nonZero.map((d) => (
        <div
          key={d.label}
          className="flex items-center justify-between gap-3 text-table"
        >
          <span className="flex items-center gap-2 text-ink">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: d.color }}
              aria-hidden="true"
            />
            {d.label}
          </span>
          <span className="font-semibold text-ink">{d.value}</span>
        </div>
      ))}
    </div>
  );
}
