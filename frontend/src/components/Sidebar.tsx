/**
 * Sidebar navigation component.
 * Shows role-appropriate navigation links with active state.
 * Developed by: MERO:TG@QP4RM
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
    Activity, Shield, Server, Bell, FileText, Settings,
    Users, Layout, LogOut, HeartPulse
} from 'lucide-react'
import styles from './Sidebar.module.css'

const NAV_ITEMS = [
    { href: '/', icon: Layout, label: 'Dashboard' },
    { href: '/devices', icon: Server, label: 'Devices' },
    { href: '/alerts', icon: Bell, label: 'Alerts' },
    { href: '/metrics', icon: Activity, label: 'Metrics' },
    { href: '/security', icon: Shield, label: 'Security' },
    { href: '/reports', icon: FileText, label: 'Reports' },
    { href: '/users', icon: Users, label: 'Users' },
    { href: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
    const pathname = usePathname()

    if (pathname === '/login') return null

    const handleLogout = () => {
        // Clear tokens from localStorage if stored there (though likely HttpOnly cookies)
        localStorage.removeItem('token')
        window.location.href = '/login'
    }

    return (
        <nav className={styles.sidebar}>
            {/* Logo */}
            <div className={styles.logo}>
                <HeartPulse size={24} color="var(--accent-red)" strokeWidth={2.5} />
                <span className={styles.logoText}>HMS</span>
            </div>

            {/* Navigation */}
            <ul className={styles.navList}>
                {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
                    const isActive = pathname === href || (href !== '/' && pathname.startsWith(href))
                    return (
                        <li key={href}>
                            <Link
                                href={href}
                                className={`${styles.navItem} ${isActive ? styles.active : ''}`}
                                title={label}
                            >
                                <Icon size={18} strokeWidth={1.8} />
                                <span className={styles.navLabel}>{label}</span>
                            </Link>
                        </li>
                    )
                })}
            </ul>

            {/* Footer */}
            <div className={styles.sidebarFooter}>
                <button className={styles.logoutBtn} type="button" onClick={handleLogout}>
                    <LogOut size={16} />
                    <span>Sign Out</span>
                </button>
            </div>
        </nav>
    )
}
