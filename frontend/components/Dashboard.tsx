import React from "react";

type Summary = {
  byMonth: { month: string; count: number; success: number }[];
  byType: { type: string; count: number }[];
  byCountry: { country_code: string; count: number }[];
  topCollaborators: { name: string; count: number }[];
};

type Props = {
  data: Summary;
};

export function Dashboard({ data }: Props) {
  // Placeholder layout. In production, use Recharts/ECharts.
  return (
    <div style={{ display: "grid", gap: "var(--bmf-space-4)" }}>
      <div className="bmf-card">
        <h3 style={{ marginTop: 0 }}>Attempts by Month</h3>
        <div style={{ display: "flex", gap: "var(--bmf-space-3)", flexWrap: "wrap" }}>
          {data.byMonth.map((m) => (
            <div key={m.month} style={{ minWidth: 80 }}>
              <div style={{ fontFamily: "var(--bmf-font-display)", fontSize: "var(--bmf-font-size-300)" }}>{m.count}</div>
              <div style={{ opacity: 0.7 }}>{m.month}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="bmf-card">
        <h3 style={{ marginTop: 0 }}>Challenge Types</h3>
        <ul>
          {data.byType.map((t) => (
            <li key={t.type}>{t.type}: {t.count}</li>
          ))}
        </ul>
      </div>
      <div className="bmf-card">
        <h3 style={{ marginTop: 0 }}>Top Collaborators</h3>
        <ol>
          {data.topCollaborators.map((c) => (
            <li key={c.name}>{c.name} ({c.count})</li>
          ))}
        </ol>
      </div>
    </div>
  );
}

