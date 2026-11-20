// Alias legibles sobre los tipos generados desde contracts/openapi.yaml (npm run gen:api).
import type { components, paths } from "./schema";

type S = components["schemas"];

export type LlmMode = S["LlmMode"];
export type CdeState = S["CdeState"];
export type Discipline = S["Discipline"];
export type Severity = S["Severity"];
export type IssueStatus = S["IssueStatus"];
export type Unit = S["Unit"];
export type Element = S["Element"];
export type Issue = S["Issue"];
export type Snapshot = S["Snapshot"];
export type FeedbackReason = S["FeedbackReason"];
export type Feedback = S["Feedback"];
export type ElementThread = S["ElementThread"];
export type ThreadEvent = ElementThread["events"][number];
export type DisciplineStats = S["DisciplineStats"];
export type Stats = S["Stats"];
export type RuleStats = Stats["by_rule"][number];
export type BudgetLine = S["BudgetLine"];
export type Budget = S["Budget"];
export type BudgetDiffLine = S["BudgetDiffLine"];
export type BudgetDiff = S["BudgetDiff"];
export type Recommendation = S["Recommendation"];
export type Health =
  paths["/health"]["get"]["responses"][200]["content"]["application/json"];

export interface IssueFilters {
  snapshot_id?: number;
  status?: IssueStatus;
  discipline?: Discipline;
  rule_id?: string;
}

export type ExportKind = "bcf" | "4d.csv" | "cobie.xlsx";

/** Contrato común entre el cliente HTTP real y el mock. */
export interface ApiClient {
  readonly source: "api" | "mock";
  health(): Promise<Health>;
  listSnapshots(): Promise<Snapshot[]>;
  setCdeState(snapshotId: number, cdeState: CdeState): Promise<Snapshot>;
  listIssues(filters?: IssueFilters): Promise<Issue[]>;
  getElementThread(guid: string): Promise<ElementThread>;
  listFeedback(): Promise<Feedback[]>;
  getStats(snapshotId?: number): Promise<Stats>;
  getBudget(snapshotId?: number): Promise<Budget>;
  getBudgetDiff(fromId: number, toId: number): Promise<BudgetDiff>;
  getRecommendations(snapshotId?: number): Promise<Recommendation[]>;
  /** URL de descarga, o null si no hay backend (modo demostración). */
  exportUrl(kind: ExportKind, snapshotId?: number): string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}
