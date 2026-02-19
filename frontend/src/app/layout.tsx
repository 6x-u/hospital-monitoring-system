/**
 * Root layout for the Hospital Infrastructure Monitoring System dashboard.
 * Provides dark mode, global styles, and navigation sidebar.
 * Developed by: MERO:TG@QP4RM
 */

import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { TopBar } from '@/components/TopBar'

export const metadata: Metadata = {
    title: 'Hospital Infrastructure Monitoring System',
    description: 'Enterprise-grade hospital infrastructure monitoring dashboard. Real-time metrics, AI anomaly detection, and automated recovery.',
    keywords: ['hospital', 'monitoring', 'infrastructure', 'security', 'healthcare'],
    authors: [{ name: 'MERO:TG@QP4RM' }],
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body>
                <div style={{ display: 'flex', minHeight: '100vh' }}>
                    <Sidebar />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <TopBar />
                        <main style={{ flex: 1, padding: '1.5rem', overflowY: 'auto' }}>
                            {children}
                        </main>
                        <footer style={{
                            padding: '0.75rem 1.5rem',
                            textAlign: 'center',
                            borderTop: '1px solid var(--border-color)',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)',
                        }}>
                            Hospital Infrastructure Monitoring System v1.0.0 —{' '}
                            <span style={{ color: 'var(--accent-blue)' }}>Developed by MERO:TG@QP4RM</span>
                        </footer>
                    </div>
                </div>
            </body>
        </html>
    )
}
