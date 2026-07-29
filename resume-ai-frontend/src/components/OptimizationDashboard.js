import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './OptimizationDashboard.css';

const OptimizationDashboard = ({ matchId, resumeId }) => {
    const [suggestions, setSuggestions] = useState([]);
    const [status, setStatus] = useState('IDLE'); // 'IDLE', 'PROCESSING', 'COMPLETED'
    const [selectedTheme, setSelectedTheme] = useState('Executive');
    const [downloading, setDownloading] = useState(false);
    const pollingIntervalRef = useRef(null);

    // Helper to get fully resolved backend URL for browser direct window loads (e.g. PDF downloads)
    const getBackendUrl = (path) => {
        const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const base = isDev ? 'http://127.0.0.1:8000' : '';
        return `${base}${path}`;
    };

    // Auto-fetch existing suggestions on mount, and handle unmount cleanup
    const API_BASE_URL = process.env.REACT_APP_API_URL || '';
    useEffect(() => {
        const fetchExistingSuggestions = async () => {
            try {
                // const res = await axios.get(`/api/optimize/${matchId}/results/`);
                const res = await axios.get(`${API_BASE_URL}/api/optimize/${matchId}/results/`);
                if (res.data.status === 'COMPLETED' && res.data.data.length > 0) {
                    setSuggestions(res.data.data);
                    setStatus('COMPLETED');
                }
            } catch (err) {
                console.error("Failed to load existing suggestions:", err);
            }
        };

        fetchExistingSuggestions();

        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
            }
        };
    }, [matchId]);
    
    const startOptimization = async () => {
        try {
            setStatus('PROCESSING');
            await axios.post(`${API_BASE_URL}/api/optimize/trigger/`, { match_id: matchId });
            pollForResults();
        } catch (error) {
            console.error(error);
            setStatus('ERROR');
        }
    };

    const pollForResults = () => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
        }

        pollingIntervalRef.current = setInterval(async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/api/optimize/${matchId}/results/`);
                if (res.data.status === 'COMPLETED' && res.data.data.length > 0) {
                    setSuggestions(res.data.data);
                    setStatus('COMPLETED');
                    clearInterval(pollingIntervalRef.current);
                    pollingIntervalRef.current = null;
                }
            } catch (err) {
                console.error(err);
            }
        }, 2000);
    };

    // --- Interactive Action: Accept Suggestions ---
    const handleAccept = async (id) => {
        try {
            await axios.post(`${API_BASE_URL}/api/suggestions/${id}/accept/`);
            setSuggestions(prev => prev.map(item => 
                item.id === id ? { ...item, status: 'ACCEPTED' } : item
            ));
        } catch (error) {
            console.error(error);
            alert("Could not apply accepted upgrade.");
        }
    };

    // --- Interactive Action: Reject Suggestions ---
    const handleReject = async (id) => {
        try {
           await axios.post(`${API_BASE_URL}/api/suggestions/${id}/reject/`);
            setSuggestions(prev => prev.map(item => 
                item.id === id ? { ...item, status: 'REJECTED' } : item
            ));
        } catch (error) {
            console.error(error);
            alert("Could not dismiss suggestion.");
        }
    };

    // --- Trigger Server Compile & Download PDF ---
    const triggerDownload = () => {
        setDownloading(true);
        setTimeout(() => setDownloading(false), 2000);
        window.open(getBackendUrl(`/api/resumes/${resumeId}/download/?theme=${selectedTheme}`), '_blank');
    };

    return (
        <div className="mt-5">
            {/* Header Section */}
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h4 className="fw-bold mb-0 text-white text-gradient-glow">
                    ✨ AI Resume Enhancer
                </h4>
                
                {status === 'IDLE' && (
                    <button 
                        className="btn btn-primary-glass" 
                        onClick={startOptimization}
                    >
                        Generate Improvements
                    </button>
                )}
                
                {status === 'PROCESSING' && (
                    <div className="d-flex align-items-center text-info px-3 py-2 rounded-pill" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>
                        <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                        <span className="fw-bold small text-white-50">Crafting suggestions...</span>
                    </div>
                )}
            </div>

            {/* --- NEW THEME SELECTOR & COMPILED PDF DOWNLOAD ROW --- */}
            {status === 'COMPLETED' && (
                <div className="glass-card p-3 mb-4 d-flex flex-wrap justify-content-between align-items-center gap-3" style={{ border: '1px solid rgba(14, 165, 233, 0.15)' }}>
                    <div className="d-flex align-items-center gap-2">
                        <span className="small text-white-50 fw-bold text-uppercase">LaTeX PDF Theme:</span>
                        <div className="btn-group btn-group-sm" style={{ background: 'rgba(0,0,0,0.2)', padding: '3px', borderRadius: '50px' }}>
                            {['Executive', 'Tech', 'Academic'].map(theme => (
                                <button
                                    key={theme}
                                    className={`btn rounded-pill px-3 py-1 border-0 small ${selectedTheme === theme ? 'btn-primary' : 'text-white-50'}`}
                                    onClick={() => setSelectedTheme(theme)}
                                    style={{ fontSize: '0.8rem' }}
                                >
                                    {theme}
                                </button>
                            ))}
                        </div>
                    </div>
                    
                    <button 
                        className="btn btn-primary-glass px-4"
                        onClick={triggerDownload}
                        disabled={downloading}
                    >
                        {downloading ? (
                            <span><span className="spinner-border spinner-border-sm me-2"/>Compiling PDF...</span>
                        ) : (
                            <span>📥 Download Upgraded Resume PDF</span>
                        )}
                    </button>
                </div>
            )}

            {/* Suggestions List */}
            {suggestions
                .filter(item => item.status !== 'REJECTED') // Hide dismissed suggestions
                .map((item, index) => {
                    const isAccepted = item.status === 'ACCEPTED';
                    
                    return (
                        <div 
                            key={index} 
                            className="glass-panel p-4 position-relative"
                            style={isAccepted ? { 
                                border: '1px solid rgba(20, 184, 166, 0.4)', 
                                background: 'rgba(20, 184, 166, 0.05)',
                                transform: 'none'
                            } : {}}
                        >
                            {/* Card Header Status */}
                            <div className="d-flex justify-content-between align-items-center mb-3">
                                <span className="category-badge">{item.category} Update</span>
                                {isAccepted && (
                                    <span className="badge bg-success px-3 py-2 rounded-pill fw-bold text-uppercase" style={{ fontSize: '0.7rem' }}>
                                        ✓ Saved to Resume
                                    </span>
                                )}
                            </div>
                            
                            {/* Content comparison Grid */}
                            <div className="diff-grid" style={isAccepted ? { opacity: 0.6 } : {}}>
                                {/* Left: Original */}
                                <div>
                                    <h6 className="text-uppercase text-danger small fw-bold mb-2">Original</h6>
                                    <div className="original-box">
                                        "{item.original_text}"
                                    </div>
                                </div>

                                {/* Center: Arrow */}
                                <div className="arrow-container" style={isAccepted ? { animation: 'none' } : {}}>
                                    ➜
                                </div>

                                {/* Right: Optimized */}
                                <div>
                                    <h6 className="text-uppercase text-success small fw-bold mb-2">AI Optimized</h6>
                                    <div className="optimized-box">
                                        "{item.optimized_text}"
                                    </div>
                                </div>
                            </div>

                            {/* Footer: Reasoning */}
                            <div className="reason-text" style={isAccepted ? { opacity: 0.6 } : {}}>
                                <strong>💡 Why:</strong> {item.reason}
                            </div>

                            {/* --- INTERACTIVE ACTION BUTTON PANEL --- */}
                            {!isAccepted && (
                                <div className="d-flex justify-content-end gap-2 mt-4 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                    <button 
                                        className="btn btn-outline-secondary btn-sm px-3 rounded-pill text-white-50"
                                        onClick={() => handleReject(item.id)}
                                        style={{ fontSize: '0.8rem', border: '1px solid rgba(255,255,255,0.1)' }}
                                    >
                                        Dismiss
                                    </button>
                                    <button 
                                        className="btn btn-success btn-sm px-3 rounded-pill fw-bold"
                                        onClick={() => handleAccept(item.id)}
                                        style={{ fontSize: '0.8rem' }}
                                    >
                                        Accept Upgrade
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
        </div>
    );
};

export default OptimizationDashboard;
