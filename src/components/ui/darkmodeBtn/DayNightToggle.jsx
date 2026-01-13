"use client";

import { useDarkMode } from "../../../context/DarkModeContext";
import styles from "./DayNightToggle.module.scss";

export default function DayNightToggle() {
  const { isDarkMode, toggleDarkMode } = useDarkMode();

  return (
    <div
      className={`${styles.toggleBtn} ${isDarkMode ? styles.active : ""}`}
      onClick={toggleDarkMode}
    >
      <span className={styles.switch}>
        {/* Sun Icon */}
        <svg
          className={`${styles.icon} ${styles.sunIcon}`}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="12" cy="12" r="5" fill="#FFD700" />
          <g stroke="#FFD700" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="1" x2="12" y2="4" />
            <line x1="12" y1="20" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="6.34" y2="6.34" />
            <line x1="17.66" y1="17.66" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="4" y2="12" />
            <line x1="20" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="6.34" y2="17.66" />
            <line x1="17.66" y1="6.34" x2="19.78" y2="4.22" />
          </g>
        </svg>

        {/* Moon Icon */}
        <svg
          className={`${styles.icon} ${styles.moonIcon}`}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
            fill="#F5F5DC"
            stroke="#F5F5DC"
            strokeWidth="1"
          />
        </svg>
      </span>
    
      {/* Stars */}
      <div className={styles.stars}>
        <span
          className={styles.star}
          style={{ "--delay": "0s", "--x": "25%", "--y": "20%" }}
        />
        <span
          className={styles.star}
          style={{ "--delay": "0.2s", "--x": "40%", "--y": "40%" }}
        />
        <span
          className={styles.star}
          style={{ "--delay": "0.4s", "--x": "30%", "--y": "60%" }}
        />
        <span
          className={styles.star}
          style={{ "--delay": "0.1s", "--x": "15%", "--y": "35%" }}
        />
        <span
          className={styles.star}
          style={{ "--delay": "0.3s", "--x": "45%", "--y": "55%" }}
        />
      </div>
    </div>
  );
}
