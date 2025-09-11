import React, { useState, useEffect } from "react";
import { Bell } from "lucide-react";
import { useAuth } from "./AuthContext";

const NotificationBell = () => {
  const { token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!token) return;

    const fetchNotifications = async () => {
      try {
        const response = await fetch(
          "http://localhost:8000/api/notifications/",
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (response.ok) {
          const data = await response.json();
          setNotifications(data);
        }
      } catch (error) {
        console.error("Failed to fetch notifications:", error);
      }
    };

    fetchNotifications();
    // Optional: Poll for new notifications every 60 seconds
    const intervalId = setInterval(fetchNotifications, 60000);

    return () => clearInterval(intervalId); // Cleanup on component unmount
  }, [token]);

  const handleBellClick = async () => {
    setIsOpen(!isOpen);
    // If opening the dropdown and there are unread notifications, mark them as read
    if (!isOpen && unreadCount > 0) {
      try {
        await fetch("http://localhost:8000/api/notifications/read", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        // Refresh notifications to show them as "read" (optional, for UI change)
        const updatedNotifications = notifications.map((n) => ({
          ...n,
          is_read: true,
        }));
        setNotifications(updatedNotifications);
      } catch (error) {
        console.error("Failed to mark notifications as read:", error);
      }
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="relative">
      <button onClick={handleBellClick} className="relative">
        <Bell className="text-gray-600 hover:text-blue-600" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white border rounded-lg shadow-xl z-10">
          <div className="p-3 font-bold border-b">Notifications</div>
          <ul className="py-1 max-h-96 overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((notif) => (
                <li
                  key={notif.id}
                  className={`px-4 py-2 text-sm text-gray-700 ${
                    !notif.is_read ? "font-bold" : ""
                  }`}
                >
                  {notif.message}
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(notif.created_at).toLocaleString()}
                  </div>
                </li>
              ))
            ) : (
              <li className="px-4 py-2 text-sm text-gray-500">
                You have no notifications.
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
