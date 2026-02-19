'use client'

import { useState, useEffect, useCallback } from 'react'
import { CheckCircle, XCircle, Clock, Filter, RefreshCw, AlertTriangle, AlertOctagon, Info } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_URL

interface Alert {
    id: string
    device_id: string
    alert_type: string
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
    title: string
    message: string
    status: 'active' | 'acknowledged' | 'resolved' | 'suppressed'
    is_acknowledged: boolean
    metric_value: number | null
    threshold_value: number | null
    anomaly_score: number | null
    created_at: string
}

const SeverityIcon = ({ severity }: { severity: string }) => {
    const props = { size: 14, strokeWidth: 2 }
    if (severity === 'critical') return <AlertOctagon {...props} color="var(--severity-critical)" />
    if (severity === 'high') return <AlertTriangle {...props} color="var(--severity-high)" />
    if (severity === 'medium') return <AlertTriangle {...props} color="var(--severity-medium)" />
    return <Info {...props} color="var(--severity-info)" />
}

export default function AlertsPage() {
    const { lastMessage } = useWebSocket()
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState<'all' | 'active' | 'critical'>('active')
    const [page, setPage] = useState(1)
    const [total, setTotal] = useState(0)
    const LIMIT = 20

    const fetchAlerts = useCallback(async () => {
        const token = localStorage.getItem('access_token')
        const params: Record<string, string | number> = { limit: LIMIT, offset: (page - 1) * LIMIT }
        if (filter === 'active') params.status = 'active'
        if (filter === 'critical') { params.status = 'active'; params.severity = 'critical' }
        try {
            const res = await axios.get(`${API}/alerts`, {
                params,
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            })
            setAlerts(res.data.items ?? [])
            setTotal(res.data.total ?? 0)
        } catch {
            setAlerts([])
        } finally {
            setLoading(false)
        }
    }, [filter, page])

    useEffect(() => { fetchAlerts() }, [fetchAlerts])

    useEffect(() => {
        if (!lastMessage) return
        const msg = lastMessage as { type?: string }
        if (msg.type === 'alert_new' || msg.type === 'alert_ack' || msg.type === 'alert_resolve') {
            fetchAlerts()
        }
    }, [lastMessage, fetchAlerts])

    const acknowledge = async (id: string) => {
        const token = localStorage.getItem('access_token')
        await axios.post(`${API}/alerts/${id}/acknowledge`, {}, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        fetchAlerts()
    }

    const resolve = async (id: string) => {
        const token = localStorage.getItem('access_token')
        await axios.post(`${API}/alerts/${id}/resolve`, {}, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        fetchAlerts()
    }

    const totalPages = Math.ceil(total / LIMIT)

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Alerts</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{total} total</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    {(['all', 'active', 'critical'] as const).map(f => (
                        <button
                            key={f}
                            className={`btn ${filter === f ? 'btn-primary' : ''}`}
                            style={filter !== f ? { background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' } : {}}
                            onClick={() => { setFilter(f); setPage(1) }}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                    <button className="btn" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)' }} onClick={fetchAlerts}>
                        <RefreshCw size={14} />
                    </button>
                </div>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
                            {['Severity', 'Title', 'Type', 'Device', 'Value', 'Time', 'Status', 'Actions'].map(h => (
                                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 500 }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading alerts...</td></tr>
                        ) : alerts.length === 0 ? (
                            <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>No alerts found</td></tr>
                        ) : alerts.map(a => (
                            <tr key={a.id} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.15s' }}
                                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                                onMouseLeave={e => (e.currentTarget.style.background = '')}
                            >
                                <td style={{ padding: '12px 16px' }}>
                                    <span className={`status-badge severity-${a.severity}`} style={{ padding: '3px 8px', borderRadius: 100 }}>
                                        <SeverityIcon severity={a.severity} />
                                        {a.severity}
                                    </span>
                                </td>
                                <td style={{ padding: '12px 16px', maxWidth: 240 }}>
                                    <p style={{ fontWeight: 500 }}>{a.title}</p>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.message}</p>
                                </td>
                                <td style={{ padding: '12px 16px', color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: '0.8rem' }}>{a.alert_type}</td>
                                <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>{a.device_id.slice(0, 8)}…</td>
                                <td style={{ padding: '12px 16px' }}>
                                    {a.metric_value != null ? <span style={{ fontVariantNumeric: 'tabular-nums' }}>{a.metric_value.toFixed(1)}</span> : '—'}
                                </td>
                                <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                    {new Date(a.created_at).toLocaleString()}
                                </td>
                                <td style={{ padding: '12px 16px' }}>
                                    <span style={{
                                        display: 'inline-flex', alignItems: 'center', gap: 4,
                                        padding: '3px 8px', borderRadius: 100, fontSize: '0.75rem', fontWeight: 600,
                                        background: a.status === 'active' ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                                        color: a.status === 'active' ? 'var(--accent-red)' : 'var(--accent-green)',
                                    }}>
                                        {a.status}
                                    </span>
                                </td>
                                <td style={{ padding: '12px 16px' }}>
                                    <div style={{ display: 'flex', gap: 4 }}>
                                        {!a.is_acknowledged && a.status === 'active' && (
                                            <button className="btn" style={{ padding: '4px 8px', fontSize: '0.75rem', background: 'rgba(245,158,11,0.12)', color: 'var(--accent-yellow)', border: '1px solid rgba(245,158,11,0.2)' }}
                                                onClick={() => acknowledge(a.id)}>
                                                <Clock size={12} /> Ack
                                            </button>
                                        )}
                                        {a.status !== 'resolved' && (
                                            <button className="btn" style={{ padding: '4px 8px', fontSize: '0.75rem', background: 'rgba(16,185,129,0.12)', color: 'var(--accent-green)', border: '1px solid rgba(16,185,129,0.2)' }}
                                                onClick={() => resolve(a.id)}>
                                                <CheckCircle size={12} /> Resolve
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
                    <button className="btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>Previous</button>
                    <span style={{ padding: '8px 16px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{page} / {totalPages}</span>
                    <button className="btn" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>Next</button>
                </div>
            )}
        </div>
    )
}
