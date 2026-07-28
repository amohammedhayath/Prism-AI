import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import OptimizationDashboard from './OptimizationDashboard';

const JobAnalyzer = ({ resumeId }) => {
    const [jobDescription, setJobDescription] = useState('');
    const [title, setTitle] = useState('');
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState(null);
    const [status, setStatus] = useState('');
    const [activeTab, setActiveTab] = useState('report'); 
    const pollingIntervalRef = useRef(null);

    // Clean up active interval on component unmount
    useEffect(() => {
        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
            }
        };
    }, []);
/*
    const handleAnalyze = async () => {
        if (!resumeId) return;
        setAnalyzing(true);
        setResult(null); 
        setActiveTab('report'); 
        setStatus('Starting...');

        try {
            const response = await axios.post('/api/jobs/analyze/', {
                resume_id: resumeId,
                title: title || "Frontend Job Search",
                description: jobDescription
            });
            const jobId = response.data.job_id;
            setStatus('Thinking...');
            pollForResult(jobId);
        } catch (error) {
            console.error(error);
            setAnalyzing(false);
            alert("Analysis failed.");
        }
    };
*/
    const API_BASE_URL = process.env.REACT_APP_API_URL || '';

    const handleAnalyze = async () => {
        if (!resumeId) return;
        setAnalyzing(true);
        setResult(null); 
        setActiveTab('report'); 
        setStatus('Starting...');

        try {
            // ✅ Prefix with API_BASE_URL so the request goes to Cloudflare/Django!
            const response = await axios.post(`${API_BASE_URL}/api/jobs/analyze/`, {
                resume_id: resumeId,
                title: title || "Frontend Job Search",
                description: jobDescription
            });
            const jobId = response.data.job_id;
            setStatus('Thinking...');
            pollForResult(jobId);
        } catch (error) {
            console.error(error);
            setAnalyzing(false);
            alert("Analysis failed.");
        }
    };

    const pollForResult = (jobId) => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
        }

        pollingIntervalRef.current = setInterval(async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/api/jobs/${jobId}/result/`);
                if (res.data.status === "COMPLETED") {
                    clearInterval(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                    setResult(res.data);
                    setAnalyzing(false);
                    setStatus('');
                }
            } catch (err) { console.error(err); }
        }, 2000); 
    };

    return (
        <div>
            <div className="d-flex align-items-center mb-4">
                <div className="bg-primary rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style={{width: 40, height: 40}}>
                    <span className="text-white fw-bold">2</span>
                </div>
                <h4 className="mb-0">Job Match Analysis</h4>
            </div>

            {/* Input Section */}
            <div className="mb-4">
                <input 
                    type="text" 
                    className="form-control mb-3" 
                    placeholder="Job Title (e.g. Senior Python Developer)"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                />
                <textarea 
                    className="form-control mb-4" 
                    rows="6" 
                    placeholder="Paste the Job Description here..."
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                ></textarea>

                <button 
                    className="btn btn-primary-glass w-100" 
                    onClick={handleAnalyze} 
                    disabled={analyzing || !resumeId}
                >
                    {analyzing ? (
                        <span><span className="spinner-border spinner-border-sm me-2"/>AI is Analyzing...</span>
                    ) : 'Run Analysis'}
                </button>
            </div>

            {/* --- RESULTS SECTION --- */}
            {result && (
                <div className="mt-5">
                    {/* Custom Glass Tabs */}
                    <div className="d-flex justify-content-center mb-4 p-1 rounded-pill" style={{background: 'rgba(0,0,0,0.2)', width: 'fit-content', margin: '0 auto'}}>
                        <button 
                            className={`btn rounded-pill px-4 ${activeTab === 'report' ? 'btn-primary' : 'text-white-50'}`}
                            onClick={() => setActiveTab('report')}
                        >
                            Analysis Report
                        </button>
                        <button 
                            className={`btn rounded-pill px-4 ${activeTab === 'enhancer' ? 'btn-primary' : 'text-white-50'}`}
                            onClick={() => setActiveTab('enhancer')}
                        >
                            AI Enhancer
                        </button>
                    </div>

                    {/* Content Area */}
                    <div className="p-2">
                        {/* TAB 1: REPORT */}
                        <div style={{ display: activeTab === 'report' ? 'block' : 'none' }}>
                            <div className="text-center">
                                <div style={{ fontSize: '3.2rem', fontWeight: '800', 
                                    background: result.score > 70 ? 'linear-gradient(to right, #4ade80, #22c55e)' : 'linear-gradient(to right, #f87171, #ef4444)',
                                    backgroundClip: 'text', WebkitBackgroundClip: 'text', color: 'transparent',
                                    lineHeight: '1.2'
                                }}>
                                    {result.score}%
                                </div>
                                <p className="text-white-50 text-uppercase letter-spacing-2 small">Match Score</p>
                                
                                <div className="glass-card mt-4 text-start">
                                    <h6 className="text-primary mb-3 text-uppercase small fw-bold">AI Verdict</h6>
                                    <p className="lead" style={{ fontSize: '1.1rem', lineHeight: '1.7', color: '#e2e8f0' }}>
                                        "{result.justification}"
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* TAB 2: OPTIMIZATION */}
                        {result.match_id && (
                            <div style={{ display: activeTab === 'enhancer' ? 'block' : 'none' }}>
                                <OptimizationDashboard matchId={result.match_id} resumeId={resumeId} />
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobAnalyzer;
