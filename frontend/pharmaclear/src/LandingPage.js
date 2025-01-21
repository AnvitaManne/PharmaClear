import React, { useState, useEffect } from "react";
import { Search } from "lucide-react";

const AlertCard = ({ alert }) => (
  <div className="p-6 border rounded-lg mb-4 hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-2">
      <h2 className="text-xl font-semibold">{alert.title}</h2>
      <div className="flex gap-2">
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            alert.agency === "FDA"
              ? "bg-blue-600 text-white"
              : alert.agency === "EMA"
              ? "bg-emerald-500 text-white"
              : "bg-purple-600 text-white"
          }`}
        >
          {alert.agency}
        </span>
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            alert.severity === "High"
              ? "bg-red-500 text-white"
              : alert.severity === "Medium"
              ? "bg-orange-400 text-white"
              : "bg-green-500 text-white"
          }`}
        >
          {alert.severity}
        </span>
      </div>
    </div>
    <p className="text-gray-600 mb-3">{alert.description}</p>
    <div className="flex justify-between items-center">
      <div className="text-sm text-gray-500">{alert.date}</div>
      <a
        href={alert.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-500 hover:text-blue-600 flex items-center text-sm"
      >
        Source
      </a>
    </div>
  </div>
);

const LandingPage = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await fetch("http://localhost:5000/api/alerts");
      if (!response.ok) throw new Error("Failed to fetch alerts");
      const data = await response.json();
      setAlerts(data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const filteredAlerts = alerts.filter(
    (alert) =>
      alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center">
            <img
              src="/images/your-logo.png"
              alt="PharmaClear Logo"
              className="h-8 w-8"
            />
            <h1 className="text-2xl font-bold ml-2">PharmaClear</h1>
          </div>

          {/* Search Bar */}
          <div className="mt-4">
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
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {loading && <div className="text-center">Loading alerts...</div>}
        {error && <div className="text-red-500 text-center">{error}</div>}
        {!loading &&
          !error &&
          filteredAlerts.map((alert, index) => (
            <AlertCard key={index} alert={alert} />
          ))}
      </main>
    </div>
  );
};

export default LandingPage;
