import React, { useState } from "react";
import { FileText, Loader } from "lucide-react";
import { useAuth } from "./AuthContext";

const ReportButton = ({ searchQuery, alerts }) => {
  const { token } = useAuth();
  const [generating, setGenerating] = useState(false);

  const handleGenerateReport = async () => {
    if (!searchQuery || alerts.length === 0 || !token) return;

    setGenerating(true);
    try {
      const formattedAlerts = alerts.map((a) => ({
        date: a.date,
        severity: a.severity,
        description: a.description,
      }));

      const response = await fetch("http://localhost:8000/api/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: searchQuery,
          alerts: formattedAlerts,
        }),
      });

      if (!response.ok) throw new Error("Failed to generate report");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${searchQuery
        .toLowerCase()
        .replace(/\s+/g, "-")}-report.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Report generation error:", error);
    } finally {
      setGenerating(false);
    }
  };

  const isDisabled =
    generating || !searchQuery || alerts.length === 0 || !token;

  return (
    <button
      onClick={handleGenerateReport}
      disabled={isDisabled}
      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      title={!token ? "You must be logged in" : "Generate PDF Report"}
    >
      {generating ? (
        <Loader className="h-5 w-5 animate-spin" />
      ) : (
        <FileText className="h-5 w-5" />
      )}
      {generating ? "Generating..." : "Generate Report"}
    </button>
  );
};

export default ReportButton;
