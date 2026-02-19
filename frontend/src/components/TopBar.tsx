/**
 * TopBar — Header with connection status, user info, and alert count.
 * Developed by: MERO:TG@QP4RM
 */
'use client'

import { useState } from 'react'
import { Bell, Wifi, WifiOff, Shield } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'

export function TopBar() {
    const { isConnected, alertCount } = useWebSocket()

    const pathname = usePathname()
    if (pathname === '/login') return null

    return (
        <header style={{
            height: '56px',
            background: 'var(--bg-secondary)',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 1.5rem',
            gap: '1rem',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Shield size={16} color="var(--accent-blue)" />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                    Hospital Infrastructure Monitoring System
                </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                {/* WebSocket connection indicator */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isConnected ? (
                        <Wifi size={14} color="var(--accent-green)" />
                    ) : (
                        <WifiOff size={14} color="var(--accent-red)" />
                    )}
                    <span style={{
                        fontSize: '0.75rem',
                        color: isConnected ? 'var(--accent-green)' : 'var(--accent-red)',
                    }}>
                        {isConnected ? 'Live' : 'Disconnected'}
                    </span>
                </div>

                {/* Alert count */}
                <div style={{ position: 'relative', cursor: 'pointer' }}>
                    <Bell size={18} color="var(--text-secondary)" />
                    {alertCount > 0 && (
                        <span style={{
                            position: 'absolute',
                            top: '-6px',
                            right: '-6px',
                            background: 'var(--accent-red)',
                            color: '#fff',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            borderRadius: '100px',
                            padding: '1px 5px',
                            minWidth: '16px',
                            textAlign: 'center',
                        }}>
                            {alertCount > 99 ? '99+' : alertCount}
                        </span>
                    )}
                </div>

                {/* User avatar */}
                <div style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '50%',
                    background: 'var(--accent-blue)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: '#fff',
                    cursor: 'pointer',
                }}>
                    AD
                </div>
            </div>
        </header>
    )
}
