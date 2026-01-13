"use client";

import React from "react";
import ProfileCard from "../../../components/ui/abouts/ProfileCard";
import style from "./about.module.scss";
import { useDarkMode } from "../../../context/DarkModeContext";
import dynamic from "next/dynamic";

// Three.js는 SSR을 지원하지 않으므로 dynamic import 사용
const UfoEasterEgg = dynamic(
  () => import("../../../components/ui/UfoEasterEgg/UfoEasterEgg"),
  { ssr: false }
);

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

const CLOUDS_DATA = [
  {
    id: 1,
    seed: 0,
    baseFreq: 0.012,
    octaves: 4,
    scale: 170,
    top: "-25vh",
    left: "-10vw",
    delay: "0s",
    duration: "60s",
    opacity: 0.9,
  },
  {
    id: 2,
    seed: 42,
    baseFreq: 0.012,
    octaves: 3,
    scale: 150,
    top: "-28vh",
    left: "25vw",
    delay: "-15s",
    duration: "55s",
    opacity: 0.8,
  },
  {
    id: 3,
    seed: 123,
    baseFreq: 0.01,
    octaves: 4,
    scale: 160,
    top: "-22vh",
    left: "55vw",
    delay: "-30s",
    duration: "70s",
    opacity: 0.85,
  },
  {
    id: 4,
    seed: 789,
    baseFreq: 0.014,
    octaves: 3,
    scale: 140,
    top: "-18vh",
    left: "-5vw",
    delay: "-45s",
    duration: "50s",
    opacity: 0.8,
  },
  {
    id: 5,
    seed: 2024,
    baseFreq: 0.011,
    octaves: 4,
    scale: 165,
    top: "-20vh",
    left: "40vw",
    delay: "-10s",
    duration: "65s",
    opacity: 0.85,
  },
  {
    id: 6,
    seed: 555,
    baseFreq: 0.013,
    octaves: 3,
    scale: 145,
    top: "-30vh",
    left: "70vw",
    delay: "-25s",
    duration: "58s",
    opacity: 0.8,
  },
];

function About() {
  const { isDarkMode } = useDarkMode();

  return (
    <div className={style.abouts}>
      {/* 해/달 */}
      <div className={style.sun} />
      <div className={style.moon} />

      {/* 구름 SVG 필터 */}
      <svg width="0" height="0" className={style.svgFilters}>
        <defs>
          {CLOUDS_DATA.map((cloud) => (
            <filter key={cloud.id} id={`about-cloud-filter-${cloud.id}`}>
              <feTurbulence
                type="fractalNoise"
                baseFrequency={cloud.baseFreq}
                numOctaves={cloud.octaves}
                seed={cloud.seed}
              />
              <feDisplacementMap in="SourceGraphic" scale={cloud.scale} />
            </filter>
          ))}
        </defs>
      </svg>

      {/* 구름 */}
      <div className={style.clouds}>
        {CLOUDS_DATA.map((cloud) => (
          <div
            key={cloud.id}
            className={style.cloud}
            style={{
              "--filter-id": `url(#about-cloud-filter-${cloud.id})`,
              "--top": cloud.top,
              "--left": cloud.left,
              "--delay": cloud.delay,
              "--duration": cloud.duration,
              "--opacity": cloud.opacity,
            }}
          />
        ))}
      </div>

      {/* UFO 이스터에그 */}
      <UfoEasterEgg />

      {/* 별 (다크모드에서만 보임) */}
      <div className={style.stars}>
        {STARS_DATA.map((star, index) => (
          <span
            key={index}
            className={style.star}
            style={{ "--delay": star.delay, "--x": star.x, "--y": star.y }}
          />
        ))}
      </div>

      {/* 프로필 카드 */}
      <ProfileCard showUserInfo />
    </div>
  );
}

export default About;
