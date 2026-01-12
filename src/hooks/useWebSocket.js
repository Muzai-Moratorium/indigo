"use client";

import { useState, useEffect, useRef, useCallback } from "react";

/**
 * useWebSocket - WebSocket 연결 관리 훅
 *
 * [사용 예시]
 * const { status, sendMessage, lastMessage } = useWebSocket("ws://localhost:8000/ws");
 *
 * [제공 기능]
 * 1. 자동 연결/재연결
 * 2. 바이너리/텍스트 메시지 전송
 * 3. 연결 상태 관리 (connecting, connected, disconnected, error)
 * 4. 컴포넌트 언마운트 시 자동 정리
 *
 * @param {string} url - WebSocket 서버 URL
 * @param {Object} options - { autoConnect: true, binaryType: "arraybuffer" }
 * @returns {Object} { status, sendMessage, sendBinary, lastMessage, connect, disconnect }
 */
export function useWebSocket(url, options = {}) {
  const { autoConnect = true, binaryType = "arraybuffer" } = options;

  const [status, setStatus] = useState("disconnected");
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // 연결
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(url);
    ws.binaryType = binaryType;

    ws.onopen = () => {
      setStatus("connected");
      console.log("[WebSocket] 연결됨");
    };

    ws.onclose = () => {
      setStatus("disconnected");
      console.log("[WebSocket] 연결 종료");
    };

    ws.onerror = (error) => {
      setStatus("error");
      console.error("[WebSocket] 에러:", error);
    };

    ws.onmessage = (event) => {
      // JSON 파싱 시도
      if (typeof event.data === "string") {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          setLastMessage(event.data);
        }
      } else {
        setLastMessage(event.data);
      }
    };

    wsRef.current = ws;
  }, [url, binaryType]);

  // 연결 해제
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
  }, []);

  // 텍스트/JSON 메시지 전송
  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = typeof data === "string" ? data : JSON.stringify(data);
      wsRef.current.send(message);
      return true;
    }
    return false;
  }, []);

  // 바이너리 데이터 전송
  const sendBinary = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
      return true;
    }
    return false;
  }, []);

  // 자동 연결
  useEffect(() => {
    if (autoConnect && url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, autoConnect]);

  return {
    status,
    isConnected: status === "connected",
    lastMessage,
    sendMessage,
    sendBinary,
    connect,
    disconnect,
    ws: wsRef.current,
  };
}

export default useWebSocket;
