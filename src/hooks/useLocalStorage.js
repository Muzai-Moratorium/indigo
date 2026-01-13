"use client";

import { useState, useEffect } from "react";

/**
 * useLocalStorage - 로컬 스토리지와 동기화되는 상태 관리 훅
 *
 * [사용 예시]
 * const [theme, setTheme] = useLocalStorage("theme", "light");
 *
 * [동작 원리]
 * 1. 초기 로드 시 localStorage에서 값 읽기
 * 2. 상태 변경 시 자동으로 localStorage에 저장
 * 3. SSR 호환 (클라이언트에서만 localStorage 접근)
 *
 * @param {string} key - localStorage 키
 * @param {*} initialValue - 기본값
 * @returns {[*, function]} [저장된 값, 값 설정 함수]
 */
export function useLocalStorage(key, initialValue) {
  // SSR에서는 initialValue 사용, 클라이언트에서 실제 값으로 업데이트
  const [storedValue, setStoredValue] = useState(initialValue);
  const [isInitialized, setIsInitialized] = useState(false);

  // 클라이언트에서 localStorage 값 읽기
  useEffect(() => {
    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.error(`useLocalStorage: ${key} 읽기 실패`, error);
    }
    setIsInitialized(true);
  }, [key]);

  // 값 변경 시 localStorage에 저장
  useEffect(() => {
    if (!isInitialized) return;

    try {
      localStorage.setItem(key, JSON.stringify(storedValue));
    } catch (error) {
      console.error(`useLocalStorage: ${key} 저장 실패`, error);
    }
  }, [key, storedValue, isInitialized]);

  return [storedValue, setStoredValue];
}

export default useLocalStorage;
