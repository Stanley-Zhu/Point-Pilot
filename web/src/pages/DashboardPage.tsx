import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import "./dashboard.css";

/* -------------------------------------------------------------------------
 * Point Pilot dashboard page
 *
 * Requires a <QueryClientProvider> above it (TanStack Query v5).
 * Set VITE_USE_SAMPLE=true to render the built-in sample data with no backend.
 * Set VITE_API_URL if the API is not served from the same origin.
 * ---------------------------------------------------------------------- */

/* ----------------------------- Types ---------------------------------- */

export type ProgramKind = "bank" | "hotel" | "airline";

export interface BalanceAccount {
  accountId: number;
  programName: string;
  kind: ProgramKind;
  points: number;
  /** Baseline value in cents per point. null means no baseline is set. */
  cppCents: number | null;
  /** ISO timestamp, or null when the program has no expiry date on file. */
  expiresAt: string | null;
  /** Plain-language rule behind expiresAt, e.g. "12 months of inactivity". */
  expiryRule: string | null;
  neverExpires: boolean;
  /** Optional server-computed note, e.g. a poor-value flag. */
  valueNote: string | null;
}

export interface BalancesResponse {
  accounts: BalanceAccount[];
}

/** Recent balance snapshots per account, oldest first. */
export type HistoryByAccount = Record<number, number[]>;

export interface LedgerEvent {
  id: number;
  occurredAt: string;
  /** Signed: positive for earn / transfer in, negative for burn / transfer out. */
  points: number;
  note: string;
}

export type AlertKind = "expiration" | "bonus" | "anomaly";

export interface DashboardAlert {
  id: number;
  kind: AlertKind;
  title: string;
  detail: string;
}

/* ----------------------------- Formatting ----------------------------- */

const DAY_MS = 86_400_000;
const nf = new Intl.NumberFormat("en-US");
const usd = (n: number) => `$${nf.format(Math.round(n))}`;
const signed = (n: number) => `${n < 0 ? "-" : "+"}${nf.format(Math.abs(n))}`;
const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });

const KIND_LABEL: Record<ProgramKind, string> = {
  bank: "Bank",
  hotel: "Hotel",
  airline: "Airline",
};

/** Estimated dollars for an account, or null when it has no baseline. */
function valueUsd(a: BalanceAccount): number | null {
  return a.cppCents == null ? null : (a.points * a.cppCents) / 100;
}

interface Tag {
  text: string;
  warn: boolean;
}

/** Same windows as the backend sweep: 90 days to show, 30 days to warn. */
function expiryTag(a: BalanceAccount, now = Date.now()): Tag | null {
  if (a.neverExpires) return { text: "Never expires", warn: false };
  if (!a.expiresAt) return null;

  const days = Math.ceil((new Date(a.expiresAt).getTime() - now) / DAY_MS);
  if (days < 0) {
    return { text: "Past expiry date. Verify this balance.", warn: true };
  }
  if (days > 90) return null;

  const rule = a.expiryRule ? ` (${a.expiryRule})` : "";
  const when =
    days === 0 ? "Expires today" : `Expires in ${days} ${days === 1 ? "day" : "days"}`;
  return { text: `${when}${rule}`, warn: days <= 30 };
}

/** Highest dollar value first; accounts without a baseline go last. */
function sortAccounts(accounts: BalanceAccount[]): BalanceAccount[] {
  return [...accounts].sort(
    (a, b) => (valueUsd(b) ?? -1) - (valueUsd(a) ?? -1)
  );
}

/* ----------------------------- Data layer ----------------------------- */

const API_BASE: string = import.meta.env.VITE_API_URL ?? "";
const USE_SAMPLE: boolean = import.meta.env.VITE_USE_SAMPLE === "true";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`Request failed (${res.status}) for ${path}`);
  return (await res.json()) as T;
}

function useBalances() {
  return useQuery({
    queryKey: ["balances"],
    queryFn: () =>
      USE_SAMPLE
        ? Promise.resolve(SAMPLE.balances)
        : getJson<BalancesResponse>("/balances"),
  });
}

/** Sparklines are an extra. If this fails, the cards render without them. */
function useBalanceHistory() {
  return useQuery({
    queryKey: ["balances", "history"],
    queryFn: () =>
      USE_SAMPLE
        ? Promise.resolve(SAMPLE.history)
        : getJson<HistoryByAccount>("/balances/history?days=90&bucket=week"),
  });
}

/** Alerts are an extra. If this fails, the strip is hidden. */
function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: () =>
      USE_SAMPLE
        ? Promise.resolve(SAMPLE.alerts)
        : getJson<DashboardAlert[]>("/alerts"),
  });
}

/** Loaded only after a card is expanded. */
function useLedgerPreview(accountId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["ledger", accountId, "preview"],
    enabled,
    queryFn: () =>
      USE_SAMPLE
        ? Promise.resolve(SAMPLE.ledger[accountId] ?? [])
        : getJson<LedgerEvent[]>(`/ledger?account_id=${accountId}&limit=3`),
  });
}

/* ----------------------------- Components ----------------------------- */

function PortfolioHeader({ accounts }: { accounts: BalanceAccount[] }) {
  const totalPoints = accounts.reduce((sum, a) => sum + a.points, 0);
  const totalValue = accounts.reduce((sum, a) => sum + (valueUsd(a) ?? 0), 0);
  const unvalued = accounts.filter((a) => a.cppCents == null).length;

  return (
    <header className="pp-header">
      <h1>Estimated portfolio value</h1>
      <div className="pp-total">{usd(totalValue)}</div>
      <p className="pp-sub">
        {nf.format(totalPoints)} points across {accounts.length}{" "}
        {accounts.length === 1 ? "program" : "programs"}
        {unvalued > 0 &&
          `. ${unvalued} without a value baseline, left out of the total.`}
      </p>
    </header>
  );
}

function AlertStrip({ alerts }: { alerts: DashboardAlert[] }) {
  if (alerts.length === 0) return null;
  return (
    <section className="pp-alerts" aria-label="Alerts">
      {alerts.map((a) => (
        <div
          key={a.id}
          className={`pp-alert${a.kind === "expiration" ? " pp-exp" : ""}`}
        >
          <b>{a.title}</b>
          <span>{a.detail}</span>
        </div>
      ))}
    </section>
  );
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;

  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const step = 300 / (values.length - 1);
  const points = values
    .map((v, i) => `${(i * step).toFixed(1)},${(28 - ((v - min) / range) * 24).toFixed(1)}`)
    .join(" ");

  return (
    <svg
      className="pp-spark"
      viewBox="0 0 300 32"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function BalanceCard({
  account,
  history,
}: {
  account: BalanceAccount;
  history?: number[];
}) {
  const [open, setOpen] = useState(false);
  const ledger = useLedgerPreview(account.accountId, open);

  const value = valueUsd(account);
  const tag = expiryTag(account);
  const logId = `ledger-preview-${account.accountId}`;

  return (
    <article className="pp-card">
      <button
        type="button"
        className="pp-card-btn"
        aria-expanded={open}
        aria-controls={logId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="pp-top">
          <span className="pp-name">{account.programName}</span>
          <span className="pp-kind">{KIND_LABEL[account.kind]}</span>
        </span>

        <span className="pp-pts">
          {nf.format(account.points)}
          <small>points</small>
        </span>

        <span className="pp-val">
          <span>{value == null ? "No value baseline set" : `About ${usd(value)}`}</span>
          {account.cppCents != null && (
            <span>{account.cppCents.toFixed(1)} cents each</span>
          )}
        </span>

        {history && <Sparkline values={history} />}

        {tag && (
          <span className={`pp-tag${tag.warn ? " pp-warn" : ""}`}>{tag.text}</span>
        )}
        {account.valueNote && <span className="pp-tag">{account.valueNote}</span>}
      </button>

      <div id={logId} className="pp-log" hidden={!open}>
        {open && (
          <>
            {ledger.isPending && <p>Loading events…</p>}
            {ledger.isError && (
              <p role="alert">
                Couldn't load events.{" "}
                <button type="button" className="pp-link" onClick={() => ledger.refetch()}>
                  Try again
                </button>
              </p>
            )}
            {ledger.data?.length === 0 && <p>No events yet.</p>}
            {ledger.data?.map((e) => (
              <div key={e.id} className="pp-event">
                <span>{shortDate(e.occurredAt)}</span>
                <span>{signed(e.points)}</span>
                <span>{e.note}</span>
              </div>
            ))}
            <a className="pp-link" href={`/ledger?account_id=${account.accountId}`}>
              View full ledger
            </a>
          </>
        )}
      </div>
    </article>
  );
}

/* ----------------------------- Page ----------------------------------- */

export default function DashboardPage() {
  const balances = useBalances();
  const history = useBalanceHistory();
  const alerts = useAlerts();

  const accounts = useMemo(
    () => sortAccounts(balances.data?.accounts ?? []),
    [balances.data]
  );

  let body: ReactNode;
  if (balances.isPending) {
    body = (
      <div className="pp-state" aria-busy="true">
        Loading balances…
      </div>
    );
  } else if (balances.isError) {
    body = (
      <div className="pp-state" role="alert">
        <b>Couldn't load your balances.</b>
        <span>Check that the API is running, then try again.</span>
        <button type="button" className="pp-link" onClick={() => balances.refetch()}>
          Try again
        </button>
      </div>
    );
  } else if (accounts.length === 0) {
    body = (
      <div className="pp-state">
        <b>No accounts yet.</b>
        <span>Add a program and enter its opening balance to get started.</span>
        <a className="pp-link" href="/accounts/new">
          Add your first program
        </a>
      </div>
    );
  } else {
    body = (
      <>
        <PortfolioHeader accounts={accounts} />
        <AlertStrip alerts={alerts.data ?? []} />
        <section className="pp-grid" aria-label="Balance cards">
          {accounts.map((a) => (
            <BalanceCard key={a.accountId} account={a} history={history.data?.[a.accountId]} />
          ))}
        </section>
        <p className="pp-note">
          {USE_SAMPLE && "Sample data. "}
          Values are points × your cents-per-point baseline, which you can edit in{" "}
          <a href="/settings">Settings</a>. Select a card to see its latest ledger events.
          Chase transfers are irreversible.
        </p>
      </>
    );
  }

  return (
    <div className="pp">
      <main className="pp-main">{body}</main>
    </div>
  );
}

/* ----------------------------- Sample data ---------------------------- */
/* Used only when VITE_USE_SAMPLE=true. Delete once the API is live.       */

const SAMPLE: {
  balances: BalancesResponse;
  history: HistoryByAccount;
  alerts: DashboardAlert[];
  ledger: Record<number, LedgerEvent[]>;
} = {
  balances: {
    accounts: [
      { accountId: 1, programName: "Chase Ultimate Rewards", kind: "bank", points: 84200, cppCents: 2.0, expiresAt: null, expiryRule: null, neverExpires: false, valueNote: null },
      { accountId: 2, programName: "World of Hyatt", kind: "hotel", points: 18400, cppCents: 1.7, expiresAt: null, expiryRule: null, neverExpires: false, valueNote: null },
      {
        accountId: 3, programName: "United MileagePlus", kind: "airline", points: 42650, cppCents: 1.3,
        expiresAt: new Date(Date.now() + 24 * DAY_MS).toISOString(),
        expiryRule: "12 months of inactivity", neverExpires: false, valueNote: null,
      },
      { accountId: 4, programName: "Delta SkyMiles", kind: "airline", points: 9800, cppCents: 1.2, expiresAt: null, expiryRule: null, neverExpires: true, valueNote: null },
      { accountId: 5, programName: "Marriott Bonvoy", kind: "hotel", points: 31000, cppCents: 0.8, expiresAt: null, expiryRule: null, neverExpires: false, valueNote: "Poor value vs. Hyatt at current baselines" },
    ],
  },
  history: {
    1: [52, 58, 61, 60, 70, 76, 84],
    2: [4, 4, 19, 19, 17, 18, 18],
    3: [38, 39, 40, 41, 41, 42, 43],
    4: [6, 7, 7, 8, 9, 9, 10],
    5: [31, 31, 31, 30, 31, 31, 31],
  },
  alerts: [
    { id: 1, kind: "expiration", title: "United miles expire in 24 days", detail: "42,650 miles. Book or earn to extend." },
    { id: 2, kind: "bonus", title: "Hyatt transfer bonus ends Oct 31", detail: "+30% on Chase transfers." },
  ],
  ledger: {
    1: [
      { id: 101, occurredAt: "2026-10-03T12:00:00Z", points: 6400, note: "Dining and travel earn" },
      { id: 102, occurredAt: "2026-09-20T12:00:00Z", points: 11000, note: "Card statement earn" },
      { id: 103, occurredAt: "2026-09-02T12:00:00Z", points: -15000, note: "Transfer to World of Hyatt" },
    ],
    2: [
      { id: 201, occurredAt: "2026-09-02T12:00:00Z", points: 15000, note: "Transfer in from Chase" },
      { id: 202, occurredAt: "2026-08-14T12:00:00Z", points: -5000, note: "Free night, Chicago" },
      { id: 203, occurredAt: "2026-07-30T12:00:00Z", points: 1240, note: "Stay earn" },
    ],
    3: [
      { id: 301, occurredAt: "2026-09-28T12:00:00Z", points: 1820, note: "Flight earn, PHL to ORD" },
      { id: 302, occurredAt: "2026-08-09T12:00:00Z", points: 2000, note: "Shopping portal" },
      { id: 303, occurredAt: "2026-06-12T12:00:00Z", points: 4100, note: "Flight earn" },
    ],
    4: [
      { id: 401, occurredAt: "2026-09-15T12:00:00Z", points: 1100, note: "Flight earn" },
      { id: 402, occurredAt: "2026-08-01T12:00:00Z", points: 900, note: "Card earn" },
      { id: 403, occurredAt: "2026-06-30T12:00:00Z", points: 650, note: "Flight earn" },
    ],
    5: [
      { id: 501, occurredAt: "2026-07-04T12:00:00Z", points: 3000, note: "Stay earn" },
      { id: 502, occurredAt: "2026-05-22T12:00:00Z", points: 2400, note: "Card earn" },
      { id: 503, occurredAt: "2026-03-08T12:00:00Z", points: -25000, note: "Free night, Boston" },
    ],
  },
};
