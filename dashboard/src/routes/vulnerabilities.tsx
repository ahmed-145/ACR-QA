import { useState } from "react";
import { Link } from "react-router-dom";
import { useVulnerabilities } from "@/lib/queries";
import { Shield, ChevronLeft, ChevronRight } from "lucide-react";
import { StatusBar } from "@/components/ui/StatusBar";

const SEV_OPTS = ["", "high", "medium", "low"] as const;
const STATUS_OPTS = ["", "open", "confirmed", "dismissed", "fixed"] as const;

export function VulnerabilitiesPage() {
  const [page, setPage] = useState(0);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const limit = 50;

  const { data, isLoading } = useVulnerabilities({
    severity: severity || undefined,
    status: status || undefined,
    limit,
    offset: page * limit,
  });

  const vulns = data?.vulnerabilities ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  function resetFilters() {
    setSeverity("");
    setStatus("");
    setPage(0);
  }

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Vulnerabilities</span>
        </div>
        <span className="grow" />
        {total > 0 && (
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
            {total} total
          </span>
        )}
      </div>

      <div className="page-pad">
        <h1 className="title">Vulnerabilities</h1>
        <p className="subtitle">Deduplicated, tracked vulnerabilities across all scan runs</p>

        {/* Filters */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
          <select
            className="inp"
            style={{ width: "auto", fontSize: 12, padding: "5px 10px" }}
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(0); }}
          >
            <option value="">All severities</option>
            {SEV_OPTS.slice(1).map((s) => (
              <option key={s} value={s}>{s.toUpperCase()}</option>
            ))}
          </select>
          <select
            className="inp"
            style={{ width: "auto", fontSize: 12, padding: "5px 10px" }}
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(0); }}
          >
            <option value="">All statuses</option>
            {STATUS_OPTS.slice(1).map((s) => (
              <option key={s} value={s}>{s.replace("_", " ").toUpperCase()}</option>
            ))}
          </select>
          {(severity || status) && (
            <button className="btn-ghost" style={{ fontSize: 12 }} onClick={resetFilters}>
              Clear filters
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="empty">
            <span className="spinner" />
            Loading…
          </div>
        ) : vulns.length === 0 ? (
          <div className="empty" style={{ flexDirection: "column", gap: 12 }}>
            <Shield size={32} style={{ color: "var(--fg-5)", opacity: 0.4 }} aria-hidden />
            <p style={{ color: "var(--fg-4)" }}>
              {severity || status
                ? "No vulnerabilities match the selected filters."
                : "No vulnerabilities yet. Run a scan to populate this list."}
            </p>
            {(severity || status) && (
              <button className="btn-ghost" style={{ fontSize: 12 }} onClick={resetFilters}>
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
              {/* Header */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "80px 90px 1fr 120px 100px",
                padding: "7px 16px",
                borderBottom: "1px solid var(--border)",
                background: "var(--bg-3)",
              }}>
                {["SEV", "STATUS", "RULE / MESSAGE", "FIRST SEEN", "OWNER"].map((h) => (
                  <div key={h} style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {h}
                  </div>
                ))}
              </div>

              {vulns.map((v) => {
                const sev = v.severity.toUpperCase();
                const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";
                return (
                  <Link
                    key={v.id}
                    to={`/vuln/${v.short_id}`}
                    style={{ display: "grid", gridTemplateColumns: "80px 90px 1fr 120px 100px", padding: "10px 16px", borderBottom: "1px solid var(--border)", textDecoration: "none", color: "inherit", transition: "background 0.1s" }}
                    className="inbox-item"
                  >
                    <div><span className={`sev ${sevCls}`}>{sev}</span></div>
                    <div>
                      <span className={`vuln-status ${v.status}`} style={{ fontSize: 10, cursor: "default" }}>
                        {v.status.replace("_", " ").toUpperCase()}
                      </span>
                    </div>
                    <div style={{ overflow: "hidden" }}>
                      <div className="inbox-item-msg">{v.message ?? v.canonical_rule_id}</div>
                      <div className="inbox-item-file">{v.file_path}</div>
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)", alignSelf: "center" }}>
                      {v.first_seen_at ? new Date(v.first_seen_at).toLocaleDateString() : "—"}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--fg-5)", alignSelf: "center" }}>
                      {v.owner ?? "—"}
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 16 }}>
                <button
                  className="btn-ghost"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={14} aria-hidden />
                </button>
                <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-4)" }}>
                  {page + 1} / {totalPages}
                </span>
                <button
                  className="btn-ghost"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                  aria-label="Next page"
                >
                  <ChevronRight size={14} aria-hidden />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <StatusBar items={[
        { label: "Total", value: total },
        { label: "Shown", value: vulns.length },
      ]} />
    </>
  );
}
