import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();

  if (!token) {
    // If no token exists, redirect to the login page
    return <Navigate to="/login" />;
  }

  // If a token exists, render the page
  return children;
};

export default ProtectedRoute;
