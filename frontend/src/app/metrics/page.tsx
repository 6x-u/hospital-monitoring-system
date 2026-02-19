/**
 * Metrics Page
 * Developed by: MERO:TG@QP4RM
 */
'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card' // Assuming basic Card components
import { Activity, Server } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import axios from 'axios'

export default function MetricsPage() {
    const [summary, setSummary] = useState<any[]>([])

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const token = localStorage.getItem('token')
                const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/metrics/summary`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
                setSummary(res.data)
            } catch (err) {
                console.error(err)
            }
        }
        fetchSummary()
        const interval = setInterval(fetchSummary, 5000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div style={{ padding: '1rem' }}>
            <h1 className="text-2xl font-bold mb-6">System Metrics Overview</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {summary.map((device) => (
                    <div key={device.device_id} className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-blue-500/10 rounded-lg">
                                    <Server className="text-blue-500" size={20} />
                                </div>
                                <div>
                                    <h3 className="font-semibold">{device.hostname}</h3>
                                    <p className="text-xs text-[var(--text-muted)]">Device ID: {device.device_id.slice(0, 8)}</p>
                                </div>
                            </div>
                            <Activity className={device.anomaly_count > 0 ? "text-red-500" : "text-green-500"} size={20} />
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-[var(--text-secondary)]">CPU Usage</span>
                                <span className="font-mono font-medium">{device.avg_cpu_percent.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-[var(--bg-primary)] h-2 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full ${device.avg_cpu_percent > 80 ? 'bg-red-500' : 'bg-blue-500'}`}
                                    style={{ width: `${device.avg_cpu_percent}%` }}
                                />
                            </div>

                            <div className="flex justify-between items-center text-sm">
                                <span className="text-[var(--text-secondary)]">RAM Usage</span>
                                <span className="font-mono font-medium">{device.avg_ram_percent.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-[var(--bg-primary)] h-2 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full ${device.avg_ram_percent > 80 ? 'bg-yellow-500' : 'bg-purple-500'}`}
                                    style={{ width: `${device.avg_ram_percent}%` }}
                                />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {summary.length === 0 && (
                <div className="text-center py-20 text-[var(--text-muted)]">
                    <Activity size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No metrics data available yet.</p>
                </div>
            )}
        </div>
    )
}
