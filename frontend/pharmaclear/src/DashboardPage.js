import React, { useState } from "react";
import { Search } from "lucide-react";
import { useAuth } from "./AuthContext"; // We'll need the token
import ReportButton from "./ReportButton"; // We'll need the report button

// You can copy the AlertCard component here or import it from another file
const AlertCard = ({ alert }) => (
  <div className="p-6 border rounded-lg mb-4 hover:shadow-md transition-shadow bg-white">
    <h2 className="text-xl font-semibold mb-2">{alert.title}</h2>
    <p className="text-gray-600 mb-3">{alert.description}</p>
    <div className="flex justify-between items-center text-sm text-gray-500">
      <span>{alert.date}</span>
      <span
        className={`px-2 py-1 rounded-full text-xs font-semibold ${
          alert.severity === "high"
            ? "bg-red-100 text-red-800"
            : alert.severity === "medium"
            ? "bg-yellow-100 text-yellow-800"
            : "bg-green-100 text-green-800"
        }`}
      >
        {alert.severity.toUpperCase()}
      </span>
    </div>
  </div>
);

const DashboardPage = () => {
  const { token } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setAlerts([]);

    try {
      // 1. Fetch search results
      const searchResponse = await fetch(
        `http://localhost:8000/api/search?q=${encodeURIComponent(searchQuery)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!searchResponse.ok) {
        const errorData = await searchResponse.json();
        throw new Error(errorData.detail || "Failed to fetch alerts");
      }
      const searchData = await searchResponse.json();
      setAlerts(searchData.results);

      // 2. Save the search to history
      await fetch("http://localhost:8000/api/searches/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query_text: searchQuery }),
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h2 className="text-3xl font-bold mb-6">Compliance Search</h2>
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search alerts by drug name, compound, or description..."
            className="w-full pl-12 pr-4 py-3 border rounded-lg focus:outline-none focus:border-blue-500"
          />
        </div>
      </form>

      {loading && <div className="text-center">Searching...</div>}
      {error && <div className="text-red-500 text-center">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {!loading &&
          alerts.map((alert, index) => <AlertCard key={index} alert={alert} />)}
      </div>

      {!loading && alerts.length === 0 && searchQuery && !error && (
        <div className="text-center text-gray-500 py-10">
          No alerts found for your query.
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
