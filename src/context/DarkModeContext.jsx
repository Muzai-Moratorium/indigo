"use client";

import { createContext, useContext, useState, useEffect } from "react";

const DarkModeContext = createContext();

export function DarkModeProvider({ children }) {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // 클라이언트에서만 로컬스토리지 값 읽기
  useEffect(() => {
    const savedMode = localStorage.getItem("darkMode") === "true";
    setIsDarkMode(savedMode);
    setIsInitialized(true);
  }, []);

  useEffect(() => {
    if (!isInitialized) return;

    // 다크모드 상태를 로컬 스토리지에 저장
    localStorage.setItem("darkMode", isDarkMode.toString());

    // body에 다크모드 클래스 토글
    if (isDarkMode) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }

    // [Step] 백엔드로 테마 상태 전송 (카카오톡 메시지 테마 변경용)
    const syncThemeToBackend = async () => {
      try {
        const theme = isDarkMode ? "nyang" : "mung";
        await fetch(`http://localhost:8000/kakao/theme?theme=${theme}`, {
          method: "POST",
        });
        console.log(`[Theme] 백엔드 테마 동기화: ${theme}`);
      } catch (err) {
        console.error("[Theme] 백엔드 테마 동기화 실패:", err);
      }
    };

    syncThemeToBackend();
  }, [isDarkMode, isInitialized]);

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => !prev);
  };

  return (
    <DarkModeContext.Provider value={{ isDarkMode, toggleDarkMode }}>
      {children}
    </DarkModeContext.Provider>
  );
}

export function useDarkMode() {
  const context = useContext(DarkModeContext);
  if (!context) {
    throw new Error("useDarkMode must be used within a DarkModeProvider");
  }
  return context;
}
