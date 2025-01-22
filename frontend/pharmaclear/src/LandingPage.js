import React, { useState } from "react";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import ReportButton from "./ReportButton";

const AlertCard = ({ alert }) => (
  <div className="p-6 border rounded-lg mb-4 hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-2">
      <h2 className="text-xl font-semibold">{alert.title}</h2>
      <div className="flex gap-2">
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-600 text-white">
          Source: {alert.source}
        </span>
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            alert.severity === "high"
              ? "bg-red-500 text-white"
              : alert.severity === "medium"
              ? "bg-orange-400 text-white"
              : "bg-green-500 text-white"
          }`}
        >
          Severity:{" "}
          {alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}
        </span>
      </div>
    </div>
    <p className="text-gray-600 mb-3">{alert.description}</p>

    {/* Components/Tags */}
    {alert.components && alert.components.length > 0 && (
      <div className="flex flex-wrap gap-2 mb-3">
        {alert.components.map((component, idx) => (
          <span
            key={idx}
            className="px-2 py-1 text-sm bg-gray-100 rounded-full"
          >
            {component}
          </span>
        ))}
      </div>
    )}

    <div className="flex justify-between items-center">
      <div className="text-sm text-gray-500">{alert.date}</div>
      {alert.source_url && (
        <a
          href={alert.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:text-blue-600 flex items-center text-sm"
        >
          View Source →
        </a>
      )}
    </div>
  </div>
);

// New Pagination Component
const Pagination = ({ currentPage, totalPages, onPageChange }) => (
  <div className="flex justify-center items-center gap-4 mt-6">
    <button
      onClick={() => onPageChange(currentPage - 1)}
      disabled={currentPage === 1}
      className="p-2 rounded-lg border enabled:hover:bg-gray-100 disabled:opacity-50"
    >
      <ChevronLeft className="h-5 w-5" />
    </button>
    <span className="text-sm">
      Page {currentPage} of {totalPages}
    </span>
    <button
      onClick={() => onPageChange(currentPage + 1)}
      disabled={currentPage === totalPages}
      className="p-2 rounded-lg border enabled:hover:bg-gray-100 disabled:opacity-50"
    >
      <ChevronRight className="h-5 w-5" />
    </button>
  </div>
);

const LandingPage = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const itemsPerPage = 10;

  const searchAlerts = async (query, page = 1) => {
    if (!query.trim()) {
      setAlerts([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:5000/api/search?q=${encodeURIComponent(
          query
        )}&page=${page}&limit=${itemsPerPage}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch alerts");
      }

      const data = await response.json();
      if (data.results) {
        setAlerts(data.results);
        setTotalResults(data.total);
      } else {
        setAlerts([]);
        setTotalResults(0);
      }
    } catch (err) {
      console.error("Search error:", err);
      setError("Failed to fetch alerts. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    searchAlerts(searchQuery, 1);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    searchAlerts(searchQuery, newPage);
  };

  const totalPages = Math.ceil(totalResults / itemsPerPage);

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center">
            <img
              src="/images/your-logo.png"
              alt="PharmaClear Logo"
              className="h-8 w-8 mr-2"
            />
            <h1 className="text-2xl font-bold ml-2 font-['Orbitron']">
              PharmaClear
            </h1>
          </div>
          {/* Search Bar */}
          <form onSubmit={handleSearch} className="mt-4">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search alerts by drug name, compound, or description..."
                className="w-full pl-12 pr-4 py-3 border rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </form>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Results Count and Report Button */}
        {totalResults > 0 && (
          <div className="flex justify-between items-center mb-4">
            <div className="text-gray-600">
              Found {totalResults} results for "{searchQuery}"
            </div>
            <ReportButton searchQuery={searchQuery} alerts={alerts} />
              
          </div>
        )}

        {loading && <div className="text-center">Searching for alerts...</div>}
        {error && <div className="text-red-500 text-center">{error}</div>}
        {!loading && alerts.length === 0 && searchQuery && (
          <div className="text-center text-gray-500">No alerts found</div>
        )}

        {/* Alert Cards */}
        {!loading &&
          !error &&
          alerts.map((alert, index) => <AlertCard key={index} alert={alert} />)}

        {/* Pagination */}
        {totalResults > itemsPerPage && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        )}
      </main>
    </div>
  );
};

export default LandingPage;
