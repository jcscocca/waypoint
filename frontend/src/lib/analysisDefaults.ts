export type AnalysisWindow = {
  analysis_start_date: string;
  analysis_end_date: string;
};

export function currentYearAnalysisWindow(now = new Date()): AnalysisWindow {
  const year = now.getFullYear();

  return {
    analysis_start_date: `${year}-01-01`,
    analysis_end_date: formatInputDate(now),
  };
}

function formatInputDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}
