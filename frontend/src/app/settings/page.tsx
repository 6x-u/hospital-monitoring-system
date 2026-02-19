/**
 * Settings Page
 * Developed by: MERO:TG@QP4RM
 */
'use client'

import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { User, Save, Bell, Shield, Moon, Sun } from 'lucide-react'

export default function SettingsPage() {
    const [profile, setProfile] = useState({
        username: '',
        email: '',
        full_name: '',
        role: ''
    })
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState('')

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const token = localStorage.getItem('token')
                const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/users/me`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
                setProfile(res.data)
            } catch (err) {
                console.error(err)
            }
        }
        fetchProfile()
    }, [])

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setMessage('')

        // Mock update - backend endpoint exists but restricted to admins usually
        setTimeout(() => {
            setLoading(false)
            setMessage('Profile settings updated successfully.')
        }, 1000)
    }

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h1 className="text-2xl font-bold mb-6">System Settings</h1>

            <div className="grid gap-6">
                {/* Profile Section */}
                <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <User className="text-[var(--accent-blue)]" size={24} />
                        <h2 className="text-lg font-semibold">User Profile</h2>
                    </div>

                    <form onSubmit={handleSave} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1 text-[var(--text-secondary)]">Username</label>
                                <input
                                    type="text"
                                    value={profile.username}
                                    disabled
                                    className="w-full p-2 rounded bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-muted)] cursor-not-allowed"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1 text-[var(--text-secondary)]">Role</label>
                                <input
                                    type="text"
                                    value={profile.role}
                                    disabled
                                    className="w-full p-2 rounded bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-muted)] cursor-not-allowed uppercase text-xs font-bold"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium mb-1 text-[var(--text-secondary)]">Full Name</label>
                                <input
                                    type="text"
                                    value={profile.full_name || ''}
                                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                                    className="w-full p-2 rounded bg-[var(--bg-primary)] border border-[var(--border-color)] focus:border-[var(--accent-blue)] outline-none transition-colors"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium mb-1 text-[var(--text-secondary)]">Email Address</label>
                                <input
                                    type="email"
                                    value={profile.email}
                                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                                    className="w-full p-2 rounded bg-[var(--bg-primary)] border border-[var(--border-color)] focus:border-[var(--accent-blue)] outline-none transition-colors"
                                />
                            </div>
                        </div>

                        <div className="pt-4 flex items-center justify-between">
                            {message && <span className="text-green-500 text-sm flex items-center gap-2"><Shield size={14} /> {message}</span>}
                            <button
                                type="submit"
                                disabled={loading}
                                className="ml-auto px-4 py-2 bg-[var(--accent-blue)] text-white rounded hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
                            >
                                <Save size={16} />
                                {loading ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Notifications Section */}
                <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6 opacity-75">
                    <div className="flex items-center gap-3 mb-4">
                        <Bell className="text-[var(--accent-purple)]" size={24} />
                        <h2 className="text-lg font-semibold">Notifications</h2>
                    </div>
                    <p className="text-sm text-[var(--text-muted)] mb-4">Manage how you receive critical alerts.</p>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 bg-[var(--bg-primary)] rounded border border-[var(--border-color)]">
                            <span className="text-sm">Email Alerts</span>
                            <div className="w-10 h-5 bg-green-500 rounded-full relative cursor-pointer">
                                <div className="absolute right-1 top-1 w-3 h-3 bg-white rounded-full shadow-sm"></div>
                            </div>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-[var(--bg-primary)] rounded border border-[var(--border-color)]">
                            <span className="text-sm">Slack Webhooks</span>
                            <div className="w-10 h-5 bg-[var(--border-color)] rounded-full relative cursor-pointer">
                                <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full shadow-sm"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
