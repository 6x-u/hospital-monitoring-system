/**
 * WebSocket hook for real-time data streaming.
 * Auto-reconnects with exponential backoff.
 * Developed by: MERO:TG@QP4RM
 */
'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/api/v1/ws'
const MAX_RECONNECT_DELAY_MS = 30000
const BASE_RECONNECT_DELAY_MS = 1000

interface WebSocketState {
    isConnected: boolean
    alertCount: number
    lastMessage: Record<string, unknown> | null
}

export function useWebSocket(): WebSocketState {
    const [isConnected, setIsConnected] = useState(false)
    const [alertCount, setAlertCount] = useState(0)
    const [lastMessage, setLastMessage] = useState<Record<string, unknown> | null>(null)

    const wsRef = useRef<WebSocket | null>(null)
    const reconnectAttempt = useRef(0)
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null)
    const isMounted = useRef(true)

    const connect = useCallback(() => {
        if (!isMounted.current) return

        // Get auth token from localStorage for WebSocket auth
        const token = typeof window !== 'undefined'
            ? localStorage.getItem('access_token')
            : null

        const url = token ? `${WS_URL}?token=${token}` : WS_URL

        try {
            const ws = new WebSocket(url)
            wsRef.current = ws

            ws.onopen = () => {
                if (!isMounted.current) return
                setIsConnected(true)
                reconnectAttempt.current = 0
            }

            ws.onmessage = (event: MessageEvent) => {
                if (!isMounted.current) return
                try {
                    const data = JSON.parse(event.data as string) as Record<string, unknown>
                    setLastMessage(data)

                    // Update alert count for new alert events
                    if (data.type === 'alert_new') {
                        setAlertCount(prev => prev + 1)
                    }
                    if (data.type === 'alert_ack' || data.type === 'alert_resolve') {
                        setAlertCount(prev => Math.max(0, prev - 1))
                    }
                } catch {
                    // Non-JSON message, ignore
                }
            }

            ws.onclose = (event: CloseEvent) => {
                if (!isMounted.current) return
                setIsConnected(false)

                // Reconnect with exponential backoff unless closed intentionally
                if (event.code !== 1000) {
                    const delay = Math.min(
                        BASE_RECONNECT_DELAY_MS * 2 ** reconnectAttempt.current,
                        MAX_RECONNECT_DELAY_MS,
                    )
                    reconnectAttempt.current += 1
                    reconnectTimer.current = setTimeout(connect, delay)
                }
            }

            ws.onerror = () => {
                ws.close()
            }
        } catch {
            // WebSocket not available (SSR)
        }
    }, [])

    useEffect(() => {
        isMounted.current = true
        connect()

        return () => {
            isMounted.current = false
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
            wsRef.current?.close(1000, 'Component unmounted')
        }
    }, [connect])

    return { isConnected, alertCount, lastMessage }
}
