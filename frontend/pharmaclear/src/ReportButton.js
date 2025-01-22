import React, { useState } from "react";
import { FileText, Loader } from "lucide-react";

const ReportButton = ({ searchQuery, alerts, onGenerateReport }) => {
  const [generating, setGenerating] = useState(false);

  const handleGenerateReport = async () => {
    if (!searchQuery || alerts.length === 0) return;

    setGenerating(true);
    try {
      const response = await fetch(
        "http://localhost:5000/api/generate-report",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: searchQuery,
            alerts: alerts,
          }),
        }
      );

      if (!response.ok) throw new Error("Failed to generate report");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        " ${searchQuery.toLowerCase().replace(/s+/g, " - ")}-report.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Report generation error:", error);
      // You might want to add error handling UI here
    } finally {
      setGenerating(false);
    }
  };

  return (
    <button
      onClick={handleGenerateReport}
      disabled={generating || !searchQuery || alerts.length === 0}
      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {generating ? (
        <Loader className="h-5 w-5 animate-spin" />
      ) : (
        <FileText className="h-5 w-5" />
      )}
      {generating ? "Generating Report..." : "Generate Report"}
    </button>
  );
};

export default ReportButton;
