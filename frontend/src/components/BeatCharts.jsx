import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { SEVERITY_COLORS, typeColor } from "../severity.js";

const tooltipStyle = {
  background: "#121821",
  border: "1px solid #223042",
  borderRadius: 8,
  color: "#e8eef5",
};

function ChartCard({ title, children }) {
  return (
    <article className="card chart-card">
      <p className="eyebrow">{title}</p>
      <div className="chart-body">{children}</div>
    </article>
  );
}

function formatDay(value) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("es-MX", { day: "numeric", month: "short" });
}

export default function BeatCharts({ stats }) {
  const total = Number(stats?.beats_total || 0);
  if (!total) {
    return <p className="muted">Aún no hay Beats</p>;
  }

  const byType = (stats.by_type || []).filter((row) => row.consumed > 0);
  const bars = (stats.by_type || []).map((row, index) => ({
    name: row.name,
    value: row.consumed,
    fill: typeColor(index),
  }));
  const pies = byType.map((row, index) => ({
    name: row.name,
    value: row.consumed,
    fill: typeColor(index),
  }));
  const severity = (stats.by_severity || [])
    .filter((row) => row.consumed > 0)
    .map((row) => ({
      name: row.label,
      value: row.consumed,
      fill: SEVERITY_COLORS[row.severity] || "#9aa8b8",
    }));
  const types = stats.by_type || [];
  const lines = (stats.by_day || []).map((row) => {
    const point = { date: formatDay(row.date), total: row.total };
    for (const item of row.by_type || []) {
      point[item.slug] = item.count;
    }
    return point;
  });

  return (
    <div className="charts">
      <ChartCard title="Volumen por tipo">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="#223042" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#9aa8b8", fontSize: 11 }} interval={0} />
            <YAxis allowDecimals={false} tick={{ fill: "#9aa8b8", fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="value" name="Beats" radius={[4, 4, 0, 0]}>
              {bars.map((row) => (
                <Cell key={row.name} fill={row.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Beats en el tiempo">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={lines} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="#223042" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: "#9aa8b8", fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fill: "#9aa8b8", fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9aa8b8" }} />
            {types.map((item, index) => (
              <Line
                key={item.id}
                type="monotone"
                dataKey={item.slug}
                name={item.name}
                stroke={typeColor(index)}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Distribución por tipo">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pies}
              dataKey="value"
              nameKey="name"
              innerRadius={48}
              outerRadius={78}
              paddingAngle={2}
            >
              {pies.map((row) => (
                <Cell key={row.name} fill={row.fill} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9aa8b8" }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Distribución por severidad">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={severity}
              dataKey="value"
              nameKey="name"
              innerRadius={48}
              outerRadius={78}
              paddingAngle={2}
            >
              {severity.map((row) => (
                <Cell key={row.name} fill={row.fill} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9aa8b8" }} />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
