import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  History,
  MessageSquare,
  Send,
  PlusCircle,
  Trash2,
} from "lucide-react";
import { useAuth } from "./AuthContext";
import ReportButton from "./ReportButton";

// src/DashboardPage.js

const AlertCard = ({ alert }) => (
  <div className="flex flex-col justify-between p-6 border rounded-lg hover:shadow-md transition-shadow bg-white">
    <div>
      <div className="flex justify-between items-start mb-2 gap-2">
        <h2 className="text-xl font-semibold">{alert.title}</h2>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
            alert.severity === "high"
              ? "bg-red-200 text-red-900"
              : alert.severity === "medium"
              ? "bg-orange-200 text-orange-900" // Changed to orange for medium
              : "bg-yellow-100 text-yellow-800" // Changed to yellow for low
          }`}
        >
          {alert.severity.toUpperCase()}
        </span>
      </div>
      <p className="text-gray-600 mb-4">{alert.description}</p>
    </div>
    <div className="flex flex-col items-start text-xs text-gray-400 border-t pt-3 mt-4">
      <div className="flex justify-between w-full mb-2">
        <span>{alert.date}</span>
        {alert.source_url && (
          <a
            href={alert.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline font-semibold"
          >
            View Source →
          </a>
        )}
      </div>
      {/* --- DISPLAYING DEBUG INFO --- */}
      <div className="font-mono">
        <div>Event ID: {alert.event_id || "N/A"}</div>
        <div>Recall #: {alert.recall_number || "N/A"}</div>
      </div>
    </div>
  </div>
);

// The component should start like this, with empty parentheses ()
const DashboardPage = () => {
  const { token } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchHistory, setSearchHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [watchlist, setWatchlist] = useState([]);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages]);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      setHistoryLoading(true);
      setWatchlistLoading(true);

      try {
        const [historyRes, watchlistRes] = await Promise.all([
          fetch("http://localhost:8000/api/searches/", {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch("http://localhost:8000/api/watchlist/", {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (!historyRes.ok) throw new Error("Failed to fetch search history.");
        if (!watchlistRes.ok) throw new Error("Failed to fetch watchlist.");

        const historyData = await historyRes.json();
        const watchlistData = await watchlistRes.json();

        setSearchHistory(historyData);
        setWatchlist(watchlistData);
      } catch (error) {
        console.error("Data fetch error:", error);
        setError("Failed to load user data.");
      } finally {
        setHistoryLoading(false);
        setWatchlistLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleSearch = async (e, queryOverride) => {
    if (e) e.preventDefault();
    const query = queryOverride || searchQuery;
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setAlerts([]);
    setChatMessages([]);

    try {
      const searchResponse = await fetch(
        `http://localhost:8000/api/search?q=${encodeURIComponent(query)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!searchResponse.ok)
        throw new Error(
          (await searchResponse.json()).detail || "Failed to fetch alerts"
        );

      const searchData = await searchResponse.json();
      setAlerts(searchData.results);

      const saveResponse = await fetch("http://localhost:8000/api/searches/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query_text: query }),
      });

      if (saveResponse.ok) {
        const newSearch = await saveResponse.json();
        setSearchHistory((prev) => [
          newSearch,
          ...prev.filter((s) => s.id !== newSearch.id),
        ]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || alerts.length === 0) return;

    const userMessage = { sender: "user", text: chatInput };
    setChatMessages((prev) => [...prev, userMessage]);
    setIsChatLoading(true);
    setChatInput("");

    try {
      const contextAlerts = alerts.map((a) => ({
        date: a.date,
        severity: a.severity,
        description: a.description,
      }));
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: chatInput,
          context_alerts: contextAlerts,
        }),
      });
      if (!response.ok)
        throw new Error("Failed to get a response from the AI.");

      const data = await response.json();
      const aiMessage = { sender: "ai", text: data.answer };
      setChatMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: "Sorry, I encountered an error. Please try again.",
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleHistoryClick = (query) => {
    setSearchQuery(query);
    handleSearch(null, query);
  };

  const handleAddToWatchlist = async () => {
    if (!searchQuery.trim() || !token) return;
    if (
      watchlist.some(
        (item) => item.query_text.toLowerCase() === searchQuery.toLowerCase()
      )
    )
      return;

    try {
      const response = await fetch("http://localhost:8000/api/watchlist/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query_text: searchQuery }),
      });
      if (!response.ok) throw new Error("Failed to add to watchlist.");
      const newItem = await response.json();
      setWatchlist((prev) => [newItem, ...prev]);
    } catch (error) {
      console.error("Add to watchlist error:", error);
    }
  };

  const handleDeleteWatchlistItem = async (itemId) => {
    if (!token) return;
    try {
      const response = await fetch(
        `http://localhost:8000/api/watchlist/${itemId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!response.ok) throw new Error("Failed to delete watchlist item.");
      setWatchlist((prev) => prev.filter((item) => item.id !== itemId));
    } catch (error) {
      console.error("Delete watchlist item error:", error);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-4 gap-8">
      <div className="lg:col-span-3">
        <h2 className="text-3xl font-bold mb-6">Compliance Search</h2>
        <form onSubmit={handleSearch} className="mb-6">
          <div className="flex items-center gap-2">
            <div className="relative flex-grow">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search alerts by drug name, compound, or description..."
                className="w-full pl-12 pr-4 py-3 border rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            <button
              type="button"
              onClick={handleAddToWatchlist}
              title="Add to Watchlist"
              className="p-3 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              <PlusCircle className="h-6 w-6 text-gray-600" />
            </button>
          </div>
        </form>

        {alerts.length > 0 && !loading && (
          <div className="flex justify-between items-center mb-4">
            <p className="text-gray-600">Found {alerts.length} alerts.</p>
            <ReportButton searchQuery={searchQuery} alerts={alerts} />
          </div>
        )}

        {loading && <div className="text-center py-10">Searching...</div>}
        {error && <div className="text-red-500 text-center py-10">{error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {!loading &&
            alerts.map((alert, index) => (
              <AlertCard key={index} alert={alert} />
            ))}
        </div>

        {!loading && alerts.length === 0 && searchQuery && !error && (
          <div className="text-center text-gray-500 py-10">
            No alerts found for your query.
          </div>
        )}

        {alerts.length > 0 && !loading && (
          <div className="mt-8 border-t pt-6">
            <h3 className="text-xl font-bold mb-4 flex items-center">
              <MessageSquare className="mr-2 h-5 w-5" />
              Chat with these Results
            </h3>
            <div
              ref={chatContainerRef}
              className="h-64 overflow-y-auto bg-gray-50 p-4 rounded-lg border mb-4"
            >
              {chatMessages.length === 0 ? (
                <p className="text-gray-500 text-center">
                  Ask a question about the results above, e.g., "Which recalls
                  were Class I?"
                </p>
              ) : (
                chatMessages.map((msg, index) => (
                  <div
                    key={index}
                    className={`mb-2 p-3 rounded-lg max-w-xl ${
                      msg.sender === "user"
                        ? "bg-blue-500 text-white ml-auto"
                        : "bg-white text-gray-800 mr-auto"
                    }`}
                  >
                    {msg.text}
                  </div>
                ))
              )}
              {isChatLoading && (
                <div className="text-gray-500">PharmaClear is thinking...</div>
              )}
            </div>
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask a question..."
                className="flex-grow p-2 border rounded-lg focus:outline-none focus:border-blue-500"
                disabled={isChatLoading}
              />
              <button
                type="submit"
                className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                disabled={isChatLoading}
              >
                <Send className="h-5 w-5" />
              </button>
            </form>
          </div>
        )}
      </div>

      <aside className="lg:col-span-1 space-y-8">
        <div className="bg-gray-50 p-6 rounded-lg">
          <h3 className="text-xl font-bold mb-4 flex items-center">
            <History className="mr-2 h-5 w-5" />
            Recent Searches
          </h3>
          {historyLoading ? (
            <p>Loading...</p>
          ) : (
            <ul className="space-y-2">
              {searchHistory.slice(0, 10).map((search) => (
                <li key={search.id}>
                  <button
                    onClick={() => handleHistoryClick(search.query_text)}
                    className="text-blue-600 hover:underline text-left w-full"
                  >
                    {search.query_text}
                  </button>
                </li>
              ))}
              {searchHistory.length === 0 && (
                <p className="text-sm text-gray-500">No searches yet.</p>
              )}
            </ul>
          )}
        </div>

        <div className="bg-gray-50 p-6 rounded-lg">
          <h3 className="text-xl font-bold mb-4 flex items-center">
            <PlusCircle className="mr-2 h-5 w-5" />
            Watchlist
          </h3>
          {watchlistLoading ? (
            <p>Loading...</p>
          ) : (
            <ul className="space-y-2">
              {watchlist.map((item) => (
                <li
                  key={item.id}
                  className="flex justify-between items-center text-sm"
                >
                  <span>{item.query_text}</span>
                  <button
                    onClick={() => handleDeleteWatchlistItem(item.id)}
                    title="Remove"
                  >
                    <Trash2 className="h-4 w-4 text-red-500 hover:text-red-700" />
                  </button>
                </li>
              ))}
              {watchlist.length === 0 && (
                <p className="text-sm text-gray-500">No items on watchlist.</p>
              )}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
};

export default DashboardPage;
