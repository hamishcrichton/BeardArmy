import React from "react";

type ChallengeRow = {
  id: number;
  date_attempted?: string;
  restaurant?: string;
  country_code?: string;
  type?: string;
  collaborators?: string[];
  result?: "success" | "failure" | "unknown";
  video_id: string;
};

type Props = {
  rows: ChallengeRow[];
  hideResult?: boolean;
};

export function DataTable({ rows, hideResult = true }: Props) {
  return (
    <div className="bmf-card">
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: `1px solid var(--bmf-color-border)` }}>
            <th style={{ padding: "var(--bmf-space-2)" }}>Date</th>
            <th style={{ padding: "var(--bmf-space-2)" }}>Restaurant</th>
            <th style={{ padding: "var(--bmf-space-2)" }}>Country</th>
            <th style={{ padding: "var(--bmf-space-2)" }}>Type</th>
            <th style={{ padding: "var(--bmf-space-2)" }}>Collaborators</th>
            {!hideResult && <th style={{ padding: "var(--bmf-space-2)" }}>Result</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} style={{ borderBottom: `1px solid var(--bmf-color-border)` }}>
              <td style={{ padding: "var(--bmf-space-2)" }}>{r.date_attempted || ""}</td>
              <td style={{ padding: "var(--bmf-space-2)" }}>{r.restaurant || ""}</td>
              <td style={{ padding: "var(--bmf-space-2)" }}>{r.country_code || ""}</td>
              <td style={{ padding: "var(--bmf-space-2)" }}>{r.type || ""}</td>
              <td style={{ padding: "var(--bmf-space-2)" }}>{(r.collaborators || []).join(", ")}</td>
              {!hideResult && (
                <td style={{ padding: "var(--bmf-space-2)" }}>
                  {r.result === "success" ? "✅" : r.result === "failure" ? "❌" : "—"}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

