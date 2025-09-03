import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useNavigate,
} from "react-router-dom";
import LandingPage from "./LandingPage";
import LoginPage from "./LoginPage";
import SignUpPage from "./SignUpPage";
import DashboardPage from "./DashboardPage";
import ProtectedRoute from "./ProtectedRoute"; // <-- Import ProtectedRoute
import { useAuth } from "./AuthContext"; // <-- Import useAuth

// A small component for the Log Out button to handle navigation
const LogoutButton = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/"); // Redirect to home page after logout
  };

  return (
    <button
      onClick={handleLogout}
      className="text-gray-600 hover:text-blue-600"
    >
      Log Out
    </button>
  );
};

function App() {
  const { token } = useAuth(); // Get the token from our context

  return (
    <Router>
      <div className="min-h-screen bg-white">
        <header className="border-b">
          <nav className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <Link to="/" className="flex items-center">
              <img
                src="/your-logo.png"
                alt="PharmaClear Logo"
                className="h-8 w-8 mr-2"
              />
              <h1 className="text-2xl font-bold font-['Orbitron']">
                PharmaClear
              </h1>
            </Link>
            <div className="flex items-center gap-4">
              {token ? (
                // Show these links if the user IS logged in
                <>
                  <Link
                    to="/dashboard"
                    className="text-gray-600 hover:text-blue-600"
                  >
                    Dashboard
                  </Link>
                  <LogoutButton />
                </>
              ) : (
                // Show these links if the user IS NOT logged in
                <>
                  <Link
                    to="/login"
                    className="text-gray-600 hover:text-blue-600"
                  >
                    Log In
                  </Link>
                  <Link
                    to="/signup"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </div>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignUpPage />} />
            {/* Wrap the DashboardPage with our ProtectedRoute component */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
