'use client'

import { useState, useEffect, useCallback } from 'react'
import { Server, ShieldOff, RefreshCw, Plus, Search } from 'lucide-react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_URL

interface Device {
    id: string
    hostname: string
    ip_address: string
    device_type: string
    os_type: string
    location: string
    department: string
    is_active: boolean
    is_isolated: boolean
    agent_version: string | null
    last_seen: string | null
}

export default function DevicesPage() {
    const [devices, setDevices] = useState<Device[]>([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [page, setPage] = useState(1)
    const [total, setTotal] = useState(0)
    const LIMIT = 25

    const fetchDevices = useCallback(async () => {
        const token = localStorage.getItem('access_token')
        try {
            const res = await axios.get(`${API}/devices`, {
                params: { limit: LIMIT, offset: (page - 1) * LIMIT, search: search || undefined },
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            })
            setDevices(res.data.items ?? [])
            setTotal(res.data.total ?? 0)
        } catch {
            setDevices([])
        } finally {
            setLoading(false)
        }
    }, [page, search])

    useEffect(() => { fetchDevices() }, [fetchDevices])

    const isolate = async (id: string) => {
        const token = localStorage.getItem('access_token')
        await axios.post(`${API}/devices/${id}/isolate`, {
            reason: 'Manual isolation by admin',
            initiated_by: 'admin',
        }, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        fetchDevices()
    }

    const reinstate = async (id: string) => {
        const token = localStorage.getItem('access_token')
        await axios.post(`${API}/devices/${id}/reinstate`, {}, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        fetchDevices()
    }

    const totalPages = Math.ceil(total / LIMIT)

    const DeviceTypeBadge = ({ type }: { type: string }) => {
        const colors: Record<string, string> = { server: '#3b82f6', workstation: '#8b5cf6', iot: '#10b981', network: '#f59e0b' }
        const c = colors[type] ?? '#6b7280'
        return <span style={{ padding: '2px 8px', borderRadius: 100, fontSize: '0.75rem', fontWeight: 500, background: `${c}18`, color: c }}>{type}</span>
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Devices</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{total} registered devices</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <div style={{ position: 'relative' }}>
                        <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                        <input
                            type="text"
                            placeholder="Search hostname or IP..."
                            value={search}
                            onChange={e => { setSearch(e.target.value); setPage(1) }}
                            style={{
                                background: 'var(--bg-card)', border: '1px solid var(--border-color)',
                                borderRadius: 'var(--radius)', padding: '8px 12px 8px 32px',
                                color: 'var(--text-primary)', fontSize: '0.875rem', outline: 'none', width: 240,
                            }}
                        />
                    </div>
                    <button className="btn" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)' }} onClick={fetchDevices}>
                        <RefreshCw size={14} />
                    </button>
                </div>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
                            {['Hostname', 'IP Address', 'Type', 'OS', 'Department', 'Location', 'Agent', 'Status', 'Last Seen', 'Actions'].map(h => (
                                <th key={h} style={{ padding: '12px 14px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan={10} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>Loading devices...</td></tr>
                        ) : devices.length === 0 ? (
                            <tr><td colSpan={10} style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>No devices found</td></tr>
                        ) : devices.map(d => (
                            <tr key={d.id} style={{ borderBottom: '1px solid var(--border-color)' }}
                                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                                onMouseLeave={e => (e.currentTarget.style.background = '')}
                            >
                                <td style={{ padding: '12px 14px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <Server size={14} color="var(--accent-blue)" />
                                        <span style={{ fontWeight: 500 }}>{d.hostname}</span>
                                    </div>
                                </td>
                                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{d.ip_address}</td>
                                <td style={{ padding: '12px 14px' }}><DeviceTypeBadge type={d.device_type} /></td>
                                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>{d.os_type}</td>
                                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>{d.department}</td>
                                <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>{d.location}</td>
                                <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{d.agent_version ?? '—'}</td>
                                <td style={{ padding: '12px 14px' }}>
                                    {d.is_isolated ? (
                                        <span style={{ padding: '3px 8px', borderRadius: 100, fontSize: '0.75rem', background: 'rgba(239,68,68,0.12)', color: 'var(--accent-red)' }}>Isolated</span>
                                    ) : d.is_active ? (
                                        <span className="status-badge status-online" style={{ padding: '3px 8px' }}>
                                            <span className="dot" style={{ background: 'var(--status-online)' }} /> Online
                                        </span>
                                    ) : (
                                        <span className="status-badge status-offline" style={{ padding: '3px 8px' }}>
                                            <span className="dot" style={{ background: 'var(--status-offline)' }} /> Offline
                                        </span>
                                    )}
                                </td>
                                <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                                    {d.last_seen ? new Date(d.last_seen).toLocaleString() : '—'}
                                </td>
                                <td style={{ padding: '12px 14px' }}>
                                    {d.is_isolated ? (
                                        <button className="btn" style={{ padding: '4px 8px', fontSize: '0.75rem', background: 'rgba(16,185,129,0.12)', color: 'var(--accent-green)', border: '1px solid rgba(16,185,129,0.2)' }}
                                            onClick={() => reinstate(d.id)}>Reinstate</button>
                                    ) : (
                                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                            onClick={() => {
                                                if (confirm(`Isolate ${d.hostname}? This will cut its network access.`)) isolate(d.id)
                                            }}>
                                            <ShieldOff size={12} /> Isolate
                                        </button>
                                    )}
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
