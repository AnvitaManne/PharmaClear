import React from "react";
import { Link } from "react-router-dom";

const LandingPage = () => {
  return (
    <div className="text-center max-w-4xl mx-auto py-20 px-4">
      <h1 className="text-4xl md:text-5xl font-extrabold text-gray-800 mb-4">
        AI-Powered Pharmaceutical Intelligence
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        Streamline your compliance process. Search FDA reports, track
        components, and generate insightful summaries with PharmaClear.
      </p>
      <div className="flex justify-center gap-4">
        <Link
          to="/signup"
          className="px-8 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors"
        >
          Get Started
        </Link>
        <Link
          to="/login"
          className="px-8 py-3 bg-gray-200 text-gray-800 font-bold rounded-lg hover:bg-gray-300 transition-colors"
        >
          Log In
        </Link>
      </div>
    </div>
  );
};

export default LandingPage;
