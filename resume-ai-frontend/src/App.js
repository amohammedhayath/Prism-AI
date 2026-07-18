import React, { useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css'; // Import the new styles
import ResumeUploader from './components/ResumeUploader';
import JobAnalyzer from './components/JobAnalyzer';

function App() {
  const [resumeId, setResumeId] = useState(null);

  return (
    <div className="app-container">
      {/* Header with Custom Prism Logo */}
      <div className="text-center mb-4">
        <div className="d-flex align-items-center justify-content-center mb-2">
          <svg width="38" height="38" viewBox="0 0 100 100" style={{ filter: 'drop-shadow(0 0 8px rgba(14, 165, 233, 0.45))' }}>
            {/* Incoming White Light Ray */}
            <line x1="5" y1="58" x2="38" y2="52" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
            
            {/* Refracted spectrum rays emerging from the prism */}
            <polygon points="38,52 95,25 95,35 38,52" fill="rgba(239, 68, 68, 0.75)" /> {/* Red */}
            <polygon points="38,52 95,35 95,45 38,52" fill="rgba(245, 158, 11, 0.75)" /> {/* Orange */}
            <polygon points="38,52 95,45 95,55 38,52" fill="rgba(16, 185, 129, 0.75)" /> {/* Green */}
            <polygon points="38,52 95,55 95,65 38,52" fill="rgba(59, 130, 246, 0.75)" /> {/* Blue */}
            <polygon points="38,52 95,65 95,75 38,52" fill="rgba(139, 92, 246, 0.75)" /> {/* Violet */}
            
            {/* The Glass Prism Triangle */}
            <polygon points="50,15 15,80 85,80" fill="none" stroke="rgba(255, 255, 255, 0.95)" strokeWidth="5.5" strokeLinejoin="round" />
            {/* Glass internal refraction facet */}
            <polygon points="50,19 19,77 81,77" fill="rgba(255, 255, 255, 0.05)" />
          </svg>
          <h1 className="mb-0 ms-2" style={{ 
            background: 'linear-gradient(135deg, #ffffff 0%, #bae6fd 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: '800',
            fontSize: '2rem'
          }}>
            Prism AI
          </h1>
        </div>
        <p className="lead text-white-50" style={{ fontSize: '1rem' }}>
          Intelligent Matching & Semantic Optimization
        </p>
      </div>

      {/* Step 1: Upload (Always Visible) */}
      <div className="glass-card">
        <ResumeUploader onUploadSuccess={(id) => setResumeId(id)} />
      </div>

      {/* Step 2: Analysis (Only if resume uploaded) */}
      {resumeId && (
        <div className="glass-card animate__animated animate__fadeInUp">
           <JobAnalyzer resumeId={resumeId} />
        </div>
      )}
      
      {/* Footer */}
      <div className="text-center mt-5 text-white-50 small">
        <p>Powered by Vertex AI & Vector Search</p>
      </div>
    </div>
  );
}

export default App;