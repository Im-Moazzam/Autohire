import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface FunnelDatum {
  label: string;
  value: number;
  color: string;
}

export interface FunnelBarChartProps {
  data: FunnelDatum[];
  height?: number;
}

/** An ordered horizontal bar chart — for a pipeline/funnel where the stage
 * order itself is meaningful (unlike a donut's unordered categories). */
export function FunnelBarChart({ data, height = 280 }: FunnelBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 32, bottom: 4, left: 4 }}
      >
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="label"
          width={120}
          tick={{ fill: "var(--color-muted)", fontSize: 13 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "var(--color-canvas)" }}
          contentStyle={{
            borderRadius: 8,
            border: "1px solid var(--color-border)",
            fontSize: 13,
          }}
        />
        <Bar
          dataKey="value"
          radius={[0, 6, 6, 0]}
          isAnimationActive
          animationDuration={900}
          animationEasing="ease-out"
        >
          {data.map((d) => (
            <Cell key={d.label} fill={d.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
