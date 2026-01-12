"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/security/mediapipe";

/**
 * useMediapipeSettings - MediaPipe API 상태 관리 훅
 *
 * [사용 예시]
 * const { enabled, available, interval, toggle, setInterval } = useMediapipeSettings();
 *
 * [제공 기능]
 * 1. MediaPipe 설정 조회 (enabled, available, interval)
 * 2. 활성화/비활성화 토글
 * 3. 호출 주기 변경 (1~30 프레임)
 *
 * @returns {Object} { enabled, available, interval, loading, toggle, setInterval, refetch }
 */
export function useMediapipeSettings() {
  const [enabled, setEnabled] = useState(true);
  const [available, setAvailable] = useState(false);
  const [interval, setIntervalState] = useState(5);
  const [loading, setLoading] = useState(true);

  // 설정 조회
  const fetchSettings = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/settings`);
      if (response.ok) {
        const data = await response.json();
        setEnabled(data.enabled);
        setAvailable(data.available);
        setIntervalState(data.frameInterval);
      }
    } catch (error) {
      console.error("MediaPipe 설정 조회 실패:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 활성화/비활성화 토글
  const toggle = useCallback(async () => {
    const newValue = !enabled;
    try {
      const response = await fetch(`${API_BASE}/toggle?enabled=${newValue}`, {
        method: "POST",
      });
      if (response.ok) {
        setEnabled(newValue);
        console.log("MediaPipe:", newValue ? "ON" : "OFF");
        return true;
      }
    } catch (error) {
      console.error("MediaPipe 토글 실패:", error);
    }
    return false;
  }, [enabled]);

  // 호출 주기 변경
  const setInterval = useCallback(async (value) => {
    const interval = parseInt(value);
    if (isNaN(interval) || interval < 1 || interval > 30) return false;

    try {
      const response = await fetch(
        `${API_BASE}/interval?interval=${interval}`,
        {
          method: "POST",
        }
      );
      if (response.ok) {
        setIntervalState(interval);
        console.log("MediaPipe 주기:", interval);
        return true;
      }
    } catch (error) {
      console.error("MediaPipe 주기 변경 실패:", error);
    }
    return false;
  }, []);

  // 초기 설정 로드
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return {
    enabled,
    available,
    interval,
    loading,
    toggle,
    setInterval,
    refetch: fetchSettings,
  };
}

export default useMediapipeSettings;
