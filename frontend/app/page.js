'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

const DOMAINS = [
    { id: 'computer_science', name: 'Computer Science', icon: '💻' },
    { id: 'electrical_engineering', name: 'Electrical Eng.', icon: '⚡' },
    { id: 'biotechnology', name: 'Biotechnology', icon: '🧬' },
    { id: 'mechanical_engineering', name: 'Mechanical Eng.', icon: '⚙️' },
    { id: 'physics', name: 'Physics', icon: '⚛️' },
    { id: 'custom', name: 'Custom', icon: '🔬' },
];

const INITIAL_AGENTS = [
    { name: 'Paper Hunter', icon: '📚', description: 'Finds research papers', status: 'idle', progress: 0, current_step: '', elapsed_seconds: 0 },
    { name: 'Synthesis Agent', icon: '🧠', description: 'Analyzes & extracts insights', status: 'idle', progress: 0, current_step: '', elapsed_seconds: 0 },
    { name: 'Writing Agent', icon: '✍️', description: 'Generates literature review', status: 'idle', progress: 0, current_step: '', elapsed_seconds: 0 },
    { name: 'Verification Agent', icon: '✅', description: 'Fact-checks all claims', status: 'idle', progress: 0, current_step: '', elapsed_seconds: 0 },
];

export default function HomePage() {
    // State
    const [topic, setTopic] = useState('');
    const [domain, setDomain] = useState('custom');
    const [yearStart, setYearStart] = useState(2020);
    const [yearEnd, setYearEnd] = useState(2026);
    const [minCitations, setMinCitations] = useState(0);
    const [citationFormat, setCitationFormat] = useState('apa');
    const [isRunning, setIsRunning] = useState(false);
    const [agents, setAgents] = useState(INITIAL_AGENTS);
    const [result, setResult] = useState(null);
    const [activeTab, setActiveTab] = useState('papers');
    const [services, setServices] = useState({ ollama: false, neo4j: false, chromadb: false });
    const [error, setError] = useState(null);
    const wsRef = useRef(null);
    const pollRef = useRef(null);

    // Check backend health
    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/health`);
                if (res.ok) {
                    const data = await res.json();
                    setServices(data);
                }
            } catch {
                // Backend not running
            }
        };
        checkHealth();
        const interval = setInterval(checkHealth, 15000);
        return () => clearInterval(interval);
    }, []);

    // Start research
    const startResearch = useCallback(async () => {
        if (!topic.trim() || isRunning) return;
        setIsRunning(true);
        setError(null);
        setResult(null);
        setActiveTab('papers');
        setAgents(INITIAL_AGENTS);

        try {
            const res = await fetch(`${API_BASE}/api/research`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: topic.trim(),
                    domain,
                    year_start: yearStart,
                    year_end: yearEnd,
                    min_citations: minCitations,
                    citation_format: citationFormat,
                }),
            });

            if (!res.ok) throw new Error('Failed to start research');
            const data = await res.json();
            const researchId = data.research_id;

            // Connect WebSocket for real-time updates
            try {
                const ws = new WebSocket(`${WS_BASE}/ws/research/${researchId}`);
                wsRef.current = ws;

                ws.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    if (msg.agent_status) {
                        setAgents(msg.agent_status);
                    }
                    if (msg.type === 'completed') {
                        fetchResult(researchId);
                    }
                };

                ws.onerror = () => {
                    // Fallback to polling if WebSocket fails
                    startPolling(researchId);
                };

                ws.onclose = () => {
                    // If closed before result, start polling
                    if (!result) startPolling(researchId);
                };
            } catch {
                startPolling(researchId);
            }

            // Also poll as backup
            startPolling(researchId);
        } catch (e) {
            setError(e.message);
            setIsRunning(false);
        }
    }, [topic, domain, yearStart, yearEnd, minCitations, citationFormat, isRunning]);

    const startPolling = (researchId) => {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/research/${researchId}`);
                const data = await res.json();
                if (data.agent_status) setAgents(data.agent_status);
                if (data.status === 'completed' || data.status === 'error') {
                    clearInterval(pollRef.current);
                    setResult(data);
                    setIsRunning(false);
                    if (wsRef.current) wsRef.current.close();
                }
            } catch { /* ignore */ }
        }, 2000);
    };

    const fetchResult = async (researchId) => {
        try {
            const res = await fetch(`${API_BASE}/api/research/${researchId}`);
            const data = await res.json();
            if (data.status === 'completed' || data.status === 'error') {
                setResult(data);
                setIsRunning(false);
                if (pollRef.current) clearInterval(pollRef.current);
            }
        } catch { /* ignore */ }
    };

    // Export handler
    const handleExport = async (format) => {
        if (!result?.research_id) return;
        try {
            const res = await fetch(`${API_BASE}/api/export/${result.research_id}?format=${format}`);
            const text = await res.text();
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `literature_review.${format === 'latex' ? 'tex' : format === 'word' ? 'json' : 'md'}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export error:', e);
        }
    };

    // Cleanup
    useEffect(() => {
        return () => {
            if (wsRef.current) wsRef.current.close();
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, []);

    return (
        <div className="app-container">
            {/* ── Header ─────────────────────────────────── */}
            <header className="header">
                <div className="header-brand">
                    <div className="header-logo">🔬</div>
                    <div>
                        <div className="header-title">Research Assistant</div>
                        <div className="header-subtitle">Autonomous Multi-Agent System</div>
                    </div>
                </div>
                <div className="header-status">
                    <div className="status-indicator">
                        <div className={`status-dot ${services.ollama ? '' : 'offline'}`} />
                        Ollama {services.ollama ? 'Online' : 'Offline'}
                    </div>
                    <div className="status-indicator">
                        <div className={`status-dot ${services.neo4j ? '' : 'offline'}`} />
                        Neo4j
                    </div>
                    <div className="status-indicator">
                        <div className={`status-dot ${services.chromadb ? '' : 'offline'}`} />
                        ChromaDB
                    </div>
                </div>
            </header>

            {/* ── Research Form ──────────────────────────── */}
            <section className="research-form card animate-slideUp">
                <div className="section-label">Research Query</div>

                {/* Domain selector */}
                <div className="domain-grid">
                    {DOMAINS.map(d => (
                        <div
                            key={d.id}
                            className={`domain-card ${domain === d.id ? 'active' : ''}`}
                            onClick={() => setDomain(d.id)}
                        >
                            <span className="domain-icon">{d.icon}</span>
                            <span className="domain-name">{d.name}</span>
                        </div>
                    ))}
                </div>

                {/* Topic input */}
                <div className="form-main">
                    <div className="input-wrapper">
                        <input
                            id="topic-input"
                            className="input-field"
                            type="text"
                            placeholder='Enter research topic, e.g. "Solid-state batteries for electric vehicles"'
                            value={topic}
                            onChange={e => setTopic(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && startResearch()}
                            disabled={isRunning}
                        />
                    </div>
                    <button
                        id="start-btn"
                        className="btn-primary"
                        onClick={startResearch}
                        disabled={isRunning || !topic.trim()}
                    >
                        {isRunning ? (
                            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span className="spinner" /> Researching...
                            </span>
                        ) : '🚀 Start Research'}
                    </button>
                </div>

                {/* Filters */}
                <div className="filters-row">
                    <div className="filter-group">
                        <span className="filter-label">Year Range:</span>
                        <input
                            className="filter-input"
                            type="number"
                            value={yearStart}
                            onChange={e => setYearStart(parseInt(e.target.value) || 2020)}
                            min={1900} max={2030}
                        />
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                        <input
                            className="filter-input"
                            type="number"
                            value={yearEnd}
                            onChange={e => setYearEnd(parseInt(e.target.value) || 2026)}
                            min={1900} max={2030}
                        />
                    </div>
                    <div className="filter-group">
                        <span className="filter-label">Min Citations:</span>
                        <input
                            className="filter-input"
                            type="number"
                            value={minCitations}
                            onChange={e => setMinCitations(parseInt(e.target.value) || 0)}
                            min={0}
                        />
                    </div>
                    <div className="filter-group">
                        <span className="filter-label">Format:</span>
                        <select
                            className="filter-select"
                            value={citationFormat}
                            onChange={e => setCitationFormat(e.target.value)}
                        >
                            <option value="apa">APA</option>
                            <option value="ieee">IEEE</option>
                            <option value="harvard">Harvard</option>
                        </select>
                    </div>
                </div>
            </section>

            {error && (
                <div className="card" style={{ borderColor: 'var(--accent-red)', marginBottom: 24 }}>
                    <p style={{ color: 'var(--accent-red)' }}>⚠️ {error}</p>
                </div>
            )}

            {/* ── Agent Status ───────────────────────────── */}
            <div className="agents-grid">
                {agents.map((agent, i) => (
                    <div
                        key={i}
                        className={`agent-card ${agent.status}`}
                        style={{ '--agent-color': ['var(--agent-hunter)', 'var(--agent-synthesis)', 'var(--agent-writer)', 'var(--agent-verifier)'][i] }}
                    >
                        <div className="agent-card-header">
                            <span className="agent-icon">{agent.icon}</span>
                            <span className="agent-name">{agent.name}</span>
                            <span className={`agent-status-badge ${agent.status}`}>{agent.status}</span>
                        </div>
                        <div className="agent-step">{agent.current_step || agent.description}</div>
                        <div className="progress-bar-container">
                            <div className="progress-bar-fill" style={{ width: `${agent.progress}%` }} />
                        </div>
                        {agent.elapsed_seconds > 0 && (
                            <div className="agent-time">{agent.elapsed_seconds}s</div>
                        )}
                    </div>
                ))}
            </div>

            {/* ── Results ────────────────────────────────── */}
            {result && result.status === 'completed' && (
                <div className="animate-fadeIn">
                    {/* Ethical Badge */}
                    {result.verification?.ethical_badge && (
                        <div className="ethical-badge">
                            <div className="badge-item">
                                <div className="badge-value" style={{ color: 'var(--accent-emerald)' }}>
                                    {result.verification.plagiarism_report?.unique_percentage || 100}%
                                </div>
                                <div className="badge-label">Unique Content</div>
                            </div>
                            <div className="badge-item">
                                <div className="badge-value" style={{ color: 'var(--accent-indigo)' }}>
                                    {result.verification.ethical_badge.sources_verified}
                                </div>
                                <div className="badge-label">Sources Verified</div>
                            </div>
                            <div className="badge-item">
                                <div className="badge-value" style={{
                                    color: result.verification.overall_confidence >= 80 ? 'var(--accent-emerald)' :
                                        result.verification.overall_confidence >= 60 ? 'var(--accent-amber)' : 'var(--accent-red)'
                                }}>
                                    {result.verification.overall_confidence}%
                                </div>
                                <div className="badge-label">Confidence</div>
                            </div>
                            <div className="badge-item">
                                <div className="badge-value" style={{ color: 'var(--accent-cyan)', fontSize: 18 }}>
                                    {result.verification.ethical_badge.human_review}
                                </div>
                                <div className="badge-label">Human Review</div>
                            </div>
                        </div>
                    )}

                    {/* Tabs */}
                    <div className="tabs">
                        {[
                            { id: 'papers', label: `📚 Papers (${result.papers?.final_count || 0})` },
                            { id: 'analysis', label: '🧠 Analysis' },
                            { id: 'review', label: '✍️ Literature Review' },
                            { id: 'verification', label: '✅ Verification' },
                            { id: 'graph', label: '🔗 Knowledge Graph' },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                                onClick={() => setActiveTab(tab.id)}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Tab: Papers */}
                    {activeTab === 'papers' && (
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon">📚</div>
                                <div>
                                    <div className="card-title">Papers Found</div>
                                    <div className="card-subtitle">
                                        {result.papers?.final_count} papers from {result.papers?.queries_used?.length || 0} search queries
                                    </div>
                                </div>
                            </div>
                            <div className="paper-list">
                                {(result.papers?.items || []).map((paper, i) => (
                                    <div key={i} className="paper-item">
                                        <div className="paper-title">{paper.title}</div>
                                        <div className="paper-authors">{(paper.authors || []).join(', ')}</div>
                                        <div className="paper-meta">
                                            <span>📅 {paper.year}</span>
                                            <span>📊 {paper.citation_count} citations</span>
                                            <span className="paper-badge">{paper.source}</span>
                                            {paper.doi && (
                                                <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener"
                                                    style={{ color: 'var(--accent-indigo)', textDecoration: 'none' }}>
                                                    🔗 DOI
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Tab: Analysis */}
                    {activeTab === 'analysis' && (
                        <div className="results-container">
                            {/* Themes */}
                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon">🎯</div>
                                    <div>
                                        <div className="card-title">Research Themes</div>
                                        <div className="card-subtitle">{result.analysis?.themes?.length || 0} themes identified</div>
                                    </div>
                                </div>
                                <div className="theme-list">
                                    {(result.analysis?.themes || []).map((theme, i) => (
                                        <div key={i} className="theme-item">
                                            <div className="theme-name">{theme.name}</div>
                                            <div className="theme-desc">{theme.description}</div>
                                            <div className="theme-count">~{theme.paper_count} papers</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Trends */}
                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon">📈</div>
                                    <div>
                                        <div className="card-title">Publication Trends</div>
                                        <div className="card-subtitle">
                                            {result.analysis?.trends?.total_papers} papers | Avg {result.analysis?.trends?.avg_citations} citations
                                        </div>
                                    </div>
                                </div>
                                {result.analysis?.trends?.yearly_counts && (
                                    <>
                                        <div className="trend-bars">
                                            {Object.entries(result.analysis.trends.yearly_counts).map(([year, count]) => {
                                                const maxCount = Math.max(...Object.values(result.analysis.trends.yearly_counts));
                                                const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                                                return (
                                                    <div key={year} className="trend-bar-wrapper">
                                                        <div className="trend-count">{count}</div>
                                                        <div className="trend-bar" style={{ height: `${height}%` }} />
                                                        <div className="trend-year">{year}</div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div style={{ textAlign: 'center', marginTop: 12 }}>
                                            <span className={`trend-label ${result.analysis.trends.trend?.includes('growing') ? 'growing' : result.analysis.trends.trend === 'stable' ? 'stable' : 'declining'}`}>
                                                📊 {result.analysis.trends.trend?.replace('_', ' ').toUpperCase()}
                                            </span>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Research Gaps */}
                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon">🔍</div>
                                    <div>
                                        <div className="card-title">Research Gaps</div>
                                        <div className="card-subtitle">Opportunities for novel contributions</div>
                                    </div>
                                </div>
                                <div className="gap-list">
                                    {(result.analysis?.gaps || []).map((gap, i) => (
                                        <div key={i} className="gap-item">
                                            <div className="theme-desc">🔹 {gap.description}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Top Authors */}
                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon">👨‍🔬</div>
                                    <div>
                                        <div className="card-title">Top Authors</div>
                                        <div className="card-subtitle">Most prolific researchers</div>
                                    </div>
                                </div>
                                <div className="theme-list">
                                    {(result.analysis?.top_authors || []).slice(0, 8).map((author, i) => (
                                        <div key={i} className="theme-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontWeight: 500 }}>{author.name}</span>
                                            <span className="paper-badge">{author.paper_count} papers</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Tab: Literature Review */}
                    {activeTab === 'review' && (
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon">✍️</div>
                                <div>
                                    <div className="card-title">{result.document?.title || 'Literature Review'}</div>
                                    <div className="card-subtitle">
                                        {result.document?.metadata?.total_papers_cited} papers cited |
                                        Format: {result.document?.metadata?.citation_format?.toUpperCase()}
                                    </div>
                                </div>
                            </div>

                            {/* Export buttons */}
                            <div className="export-grid" style={{ marginBottom: 24 }}>
                                <button className="export-btn" onClick={() => handleExport('markdown')}>📝 Markdown</button>
                                <button className="export-btn" onClick={() => handleExport('latex')}>📄 LaTeX</button>
                                <button className="export-btn" onClick={() => handleExport('word')}>📋 Word (JSON)</button>
                            </div>

                            {/* Sections */}
                            {(result.document?.sections || []).map((section, i) => (
                                <div key={i} className="review-section">
                                    <div className="review-heading">
                                        {section.heading}
                                        <span className={`confidence-badge ${section.confidence >= 90 ? 'confidence-high' : section.confidence >= 70 ? 'confidence-medium' : 'confidence-low'}`}>
                                            {section.confidence}% confidence
                                        </span>
                                    </div>
                                    <div className="review-content">{section.content}</div>
                                </div>
                            ))}

                            {/* References */}
                            {result.document?.references?.length > 0 && (
                                <div className="review-section">
                                    <div className="review-heading">References</div>
                                    <div className="references-list">
                                        {result.document.references.map((ref, i) => (
                                            <div key={i} className="reference-item">
                                                <span className="reference-key">{ref.key}</span>
                                                {ref.formatted}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Tab: Verification */}
                    {activeTab === 'verification' && (
                        <div className="results-container">
                            {/* Plagiarism Check */}
                            <div className="card results-full">
                                <div className="card-header">
                                    <div className="card-icon">🛡️</div>
                                    <div>
                                        <div className="card-title">Plagiarism & Similarity Check</div>
                                        <div className="card-subtitle">
                                            {result.verification?.plagiarism_report?.total_sentences_checked || 0} sentences analyzed
                                        </div>
                                    </div>
                                </div>

                                <div className="plagiarism-split">
                                    <div className="plagiarism-panel original">
                                        <div className="plagiarism-header">Original Source Analysis</div>
                                        {(result.verification?.plagiarism_report?.flagged_sentences || []).length > 0 ? (
                                            (result.verification.plagiarism_report.flagged_sentences).map((f, i) => (
                                                <div key={i} style={{ marginBottom: 12 }}>
                                                    <div className="plagiarism-text" style={{ fontSize: 12, color: 'var(--accent-amber)' }}>
                                                        Similar to: &quot;{f.similar_to}&quot;
                                                    </div>
                                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                                                        Similarity: {(f.similarity * 100).toFixed(1)}%
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="plagiarism-text">✅ No high-similarity matches found</div>
                                        )}
                                    </div>
                                    <div className="plagiarism-panel">
                                        <div className="plagiarism-header">AI Generated Content</div>
                                        <div className="plagiarism-score">
                                            ✅ UNIQUE: {result.verification?.plagiarism_report?.unique_percentage || 100}%
                                        </div>
                                        <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
                                            <p>Sentences checked: {result.verification?.plagiarism_report?.total_sentences_checked || 0}</p>
                                            <p>Flagged: {result.verification?.plagiarism_report?.sentences_flagged || 0}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Verified Claims */}
                            <div className="card results-full">
                                <div className="card-header">
                                    <div className="card-icon">✅</div>
                                    <div>
                                        <div className="card-title">Verified Claims</div>
                                        <div className="card-subtitle">
                                            {result.verification?.verified_count}/{result.verification?.total_claims} verified |
                                            {result.verification?.flagged_count} flagged
                                        </div>
                                    </div>
                                </div>
                                <div className="paper-list">
                                    {(result.verification?.claims || []).map((claim, i) => (
                                        <div key={i} className="paper-item">
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                                                <div className="paper-title" style={{ fontSize: 13, fontWeight: 400, flex: 1 }}>
                                                    {claim.text}
                                                </div>
                                                <span className={`confidence-badge ${claim.confidence >= 90 ? 'confidence-high' : claim.confidence >= 70 ? 'confidence-medium' : 'confidence-low'}`}>
                                                    {claim.confidence}%
                                                </span>
                                            </div>
                                            <div className="paper-meta" style={{ marginTop: 6 }}>
                                                <span>📍 {claim.section}</span>
                                                <span>📚 {claim.cross_reference?.sources_found || 0} sources</span>
                                                <span className="paper-badge">{claim.cross_reference?.status || 'unknown'}</span>
                                            </div>
                                            {/* Source previews */}
                                            {claim.source_previews?.length > 0 && (
                                                <div style={{ marginTop: 8, paddingLeft: 12, borderLeft: '2px solid var(--border-medium)' }}>
                                                    {claim.source_previews.map((preview, j) => (
                                                        <div key={j} style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                                                            📄 {preview.title} — &quot;{preview.excerpt?.substring(0, 100)}...&quot;
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Tab: Knowledge Graph */}
                    {activeTab === 'graph' && (
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon">🔗</div>
                                <div>
                                    <div className="card-title">Knowledge Graph</div>
                                    <div className="card-subtitle">Interactive visualization of paper relationships</div>
                                </div>
                            </div>
                            <KnowledgeGraph researchId={result.research_id} />
                        </div>
                    )}
                </div>
            )}

            {/* Empty State */}
            {!result && !isRunning && (
                <div className="empty-state animate-fadeIn">
                    <div className="empty-icon">🔬</div>
                    <div className="empty-title">Ready to Research</div>
                    <div className="empty-desc">
                        Enter a research topic above to start. Your 4 AI agents will find papers, analyze them,
                        write a literature review, and fact-check every claim — all automatically.
                    </div>
                </div>
            )}
        </div>
    );
}


/* ── Knowledge Graph Component ─────────────────── */
function KnowledgeGraph({ researchId }) {
    const svgRef = useRef(null);
    const [graphData, setGraphData] = useState(null);

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/graph/${researchId}`);
                const data = await res.json();
                setGraphData(data);
            } catch (e) {
                console.error('Graph fetch error:', e);
            }
        };
        if (researchId) fetchGraph();
    }, [researchId]);

    useEffect(() => {
        if (!graphData || !svgRef.current) return;
        const nodes = graphData.nodes || [];
        const edges = graphData.edges || [];
        if (nodes.length === 0) return;

        // Dynamic import D3
        import('d3').then(d3 => {
            const svg = d3.select(svgRef.current);
            svg.selectAll('*').remove();

            const width = svgRef.current.clientWidth || 800;
            const height = 400;
            svg.attr('viewBox', `0 0 ${width} ${height}`);

            const colorMap = {
                paper: '#3b82f6',
                author: '#8b5cf6',
                topic: '#06b6d4',
            };

            const sizeMap = {
                paper: 6,
                author: 5,
                topic: 8,
            };

            const simulation = d3.forceSimulation(nodes)
                .force('link', d3.forceLink(edges).id(d => d.id).distance(60).strength(0.3))
                .force('charge', d3.forceManyBody().strength(-80))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(d => (sizeMap[d.type] || 5) + 4));

            const g = svg.append('g');

            // Zoom
            svg.call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', (event) => {
                g.attr('transform', event.transform);
            }));

            const link = g.append('g')
                .selectAll('line')
                .data(edges)
                .join('line')
                .attr('stroke', 'rgba(255,255,255,0.1)')
                .attr('stroke-width', 1);

            const node = g.append('g')
                .selectAll('circle')
                .data(nodes)
                .join('circle')
                .attr('r', d => sizeMap[d.type] || 5)
                .attr('fill', d => colorMap[d.type] || '#64748b')
                .attr('stroke', 'rgba(255,255,255,0.2)')
                .attr('stroke-width', 1)
                .style('cursor', 'pointer')
                .call(d3.drag()
                    .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                    .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
                    .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
                );

            // Labels for topics
            const label = g.append('g')
                .selectAll('text')
                .data(nodes.filter(n => n.type === 'topic'))
                .join('text')
                .text(d => d.label?.substring(0, 20))
                .attr('font-size', '9px')
                .attr('fill', 'var(--text-muted)')
                .attr('dx', 12);

            // Tooltip
            node.append('title').text(d => `${d.type}: ${d.label}`);

            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
                node.attr('cx', d => d.x).attr('cy', d => d.y);
                label.attr('x', d => d.x).attr('y', d => d.y);
            });
        });
    }, [graphData]);

    return (
        <div className="kg-container">
            <div className="kg-legend">
                <div className="kg-legend-item"><div className="kg-legend-dot" style={{ background: '#3b82f6' }} /> Papers</div>
                <div className="kg-legend-item"><div className="kg-legend-dot" style={{ background: '#8b5cf6' }} /> Authors</div>
                <div className="kg-legend-item"><div className="kg-legend-dot" style={{ background: '#06b6d4' }} /> Topics</div>
            </div>
            <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
            {(!graphData || (graphData.nodes || []).length === 0) && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                    Loading knowledge graph...
                </div>
            )}
        </div>
    );
}
