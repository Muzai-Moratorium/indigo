"use client";

import "../styles/globals.scss";
import styles from "./home.module.scss";
import ScrollReveal from "../components/ui/ScrollReveal/ScrollReveal";
import { useDarkMode } from "../context/DarkModeContext";

const STARS_DATA = [
  { delay: "0s", x: "25%", y: "20%" },
  { delay: "0.2s", x: "40%", y: "40%" },
  { delay: "0.4s", x: "30%", y: "60%" },
  { delay: "0.1s", x: "15%", y: "35%" },
  { delay: "0.3s", x: "45%", y: "55%" },
  { delay: "0.5s", x: "70%", y: "25%" },
  { delay: "0.15s", x: "80%", y: "45%" },
  { delay: "0.35s", x: "60%", y: "70%" },
  { delay: "0.25s", x: "10%", y: "80%" },
  { delay: "0.45s", x: "85%", y: "15%" },
];

export default function Page({ params }) {
  const { param } = params;
  const { isDarkMode } = useDarkMode();

  return (
    <div className={styles.home}>
      <div className={styles.stars}>
        {STARS_DATA.map((star, index) => (
          <span
            key={index}
            className={styles.star}
            style={{ "--delay": star.delay, "--x": star.x, "--y": star.y }}
          />
        ))}
      </div>
      <ScrollReveal
        baseOpacity={0}
        enableBlur={true}
        baseRotation={5}
        blurStrength={10}
      >
        {isDarkMode
          ? "욜로~냥 귀엽지만 강력한 홈 프로텍트! 무료로 사용해보세요!!"
          : "욜로~멍 귀엽지만 강력한 홈 프로텍트! 무료로 사용해보세요!!"}
      </ScrollReveal>
      <img
        src={isDarkMode ? "/yolo_nyang.png" : "/yolo_mung.png"}
        alt={isDarkMode ? "욜로냥" : "욜로멍"}
      />
    </div>
  );
}
