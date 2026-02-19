'use client'

import { useState, useEffect } from 'react'
import { Activity, Server, Bell, AlertTriangle, Cpu, Database, Thermometer, Wifi } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useWebSocket } from '@/hooks/useWebSocket'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_URL

interface MetricSummary {
    device_id: string
    hostname: string
    avg_cpu_percent: number | null
    avg_ram_percent: number | null
    max_temperature: number | null
    avg_latency_ms: number | null
    anomaly_count: number
    last_updated: string | null
}

interface AlertStat {
    critical: number
    high: number
    medium: number
    low: number
    total: number
}

const COLORS = ['#ef4444', '#f97316', '#f59e0b', '#3b82f6']

const KpiCard = ({
    icon: Icon, label, value, unit, color, sub
}: {
    icon: React.ElementType
    label: string
    value: string | number
    unit?: string
    color: string
    sub?: string
}) => (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</p>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                    <span className="metric-value" style={{ color }}>{value}</span>
                    {unit && <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{unit}</span>}
                </div>
                {sub && <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>{sub}</p>}
            </div>
            <div style={{ padding: 10, borderRadius: 10, background: `${color}18` }}>
                <Icon size={20} color={color} strokeWidth={1.8} />
            </div>
        </div>
    </div>
)

export default function DashboardPage() {
    const { lastMessage } = useWebSocket()
    const [summaries, setSummaries] = useState<MetricSummary[]>([])
    const [alertStats, setAlertStats] = useState<AlertStat>({ critical: 0, high: 0, medium: 0, low: 0, total: 0 })
    const [cpuHistory, setCpuHistory] = useState<{ t: string; cpu: number }[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const token = localStorage.getItem('access_token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}

        Promise.all([
            axios.get(`${API}/metrics/summary`, { headers }),
            axios.get(`${API}/alerts?limit=200&status=active`, { headers }),
        ])
            .then(([metricsRes, alertsRes]) => {
                setSummaries(metricsRes.data)
                const alerts = alertsRes.data?.items ?? []
                const stats = { critical: 0, high: 0, medium: 0, low: 0, total: alerts.length }
                for (const a of alerts) {
                    if (a.severity === 'critical') stats.critical++
                    else if (a.severity === 'high') stats.high++
                    else if (a.severity === 'medium') stats.medium++
                    else stats.low++
                }
                setAlertStats(stats)
            })
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => {
        if (!lastMessage) return
        if ((lastMessage as { type?: string }).type === 'metric_update') {
            const payload = lastMessage as { cpu_usage_percent?: number }
            if (payload.cpu_usage_percent != null) {
                setCpuHistory(prev => [
                    ...prev.slice(-29),
                    { t: new Date().toLocaleTimeString(), cpu: payload.cpu_usage_percent! },
                ])
            }
        }
    }, [lastMessage])

    const totalDevices = summaries.length
    const onlineDevices = summaries.filter(s => s.last_updated != null).length
    const avgCpu = summaries.length > 0
        ? (summaries.reduce((a, s) => a + (s.avg_cpu_percent ?? 0), 0) / summaries.length).toFixed(1)
        : '—'
    const avgRam = summaries.length > 0
        ? (summaries.reduce((a, s) => a + (s.avg_ram_percent ?? 0), 0) / summaries.length).toFixed(1)
        : '—'

    const pieData = [
        { name: 'Critical', value: alertStats.critical },
        { name: 'High', value: alertStats.high },
        { name: 'Medium', value: alertStats.medium },
        { name: 'Low', value: alertStats.low },
    ].filter(d => d.value > 0)

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Live Dashboard</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Real-time hospital infrastructure metrics</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <KpiCard icon={Server} label="Total Devices" value={loading ? '...' : totalDevices} color="var(--accent-blue)" sub={`${onlineDevices} online`} />
                <KpiCard icon={Bell} label="Active Alerts" value={loading ? '...' : alertStats.total} color="var(--accent-red)" sub={`${alertStats.critical} critical`} />
                <KpiCard icon={Cpu} label="Avg CPU Usage" value={loading ? '...' : avgCpu} unit="%" color="var(--accent-cyan)" />
                <KpiCard icon={Database} label="Avg RAM Usage" value={loading ? '...' : avgRam} unit="%" color="var(--accent-purple)" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
                <div className="card">
                    <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>CPU Usage — Live</h2>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={cpuHistory}>
                            <defs>
                                <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                            <XAxis dataKey="t" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8 }}
                                labelStyle={{ color: 'var(--text-secondary)' }}
                            />
                            <Area type="monotone" dataKey="cpu" stroke="#3b82f6" fill="url(#cpuGrad)" strokeWidth={2} dot={false} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                <div className="card">
                    <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Alert Distribution</h2>
                    {pieData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={220}>
                            <PieChart>
                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                                    {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 8 }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                            No active alerts
                        </div>
                    )}
                </div>
            </div>

            <div className="card">
                <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Device Summary</h2>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                {['Hostname', 'CPU %', 'RAM %', 'Max Temp', 'Latency', 'Anomalies', 'Last Seen'].map(h => (
                                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 500 }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</td></tr>
                            ) : summaries.length === 0 ? (
                                <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No devices registered</td></tr>
                            ) : summaries.map(s => (
                                <tr key={s.device_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{s.hostname}</td>
                                    <td style={{ padding: '10px 12px', color: (s.avg_cpu_percent ?? 0) > 85 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                                        {s.avg_cpu_percent != null ? `${s.avg_cpu_percent.toFixed(1)}%` : '—'}
                                    </td>
                                    <td style={{ padding: '10px 12px', color: (s.avg_ram_percent ?? 0) > 85 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                                        {s.avg_ram_percent != null ? `${s.avg_ram_percent.toFixed(1)}%` : '—'}
                                    </td>
                                    <td style={{ padding: '10px 12px', color: (s.max_temperature ?? 0) > 80 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                                        {s.max_temperature != null ? `${s.max_temperature.toFixed(0)}°C` : '—'}
                                    </td>
                                    <td style={{ padding: '10px 12px' }}>{s.avg_latency_ms != null ? `${s.avg_latency_ms.toFixed(0)} ms` : '—'}</td>
                                    <td style={{ padding: '10px 12px' }}>
                                        <span style={{ color: s.anomaly_count > 0 ? 'var(--accent-red)' : 'var(--text-muted)' }}>
                                            {s.anomaly_count}
                                        </span>
                                    </td>
                                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                        {s.last_updated ? new Date(s.last_updated).toLocaleString() : '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
