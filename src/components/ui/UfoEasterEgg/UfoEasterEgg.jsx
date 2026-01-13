"use client";

import { useState, useEffect, Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import styles from "./UfoEasterEgg.module.scss";

// UFO 3D 모델 컴포넌트 - 회전만 담당
function UfoModel() {
  const { scene } = useGLTF("/Flying saucer.glb");
  const meshRef = useRef();

  useFrame((state, delta) => {
    if (meshRef.current) {
      // 회전 애니메이션만
      meshRef.current.rotation.y += delta * 3;
    }
  });

  return (
    <primitive ref={meshRef} object={scene} scale={0.02} position={[0, 0, 0]} />
  );
}

// 메인 UFO 이스터에그 컴포넌트
export default function UfoEasterEgg() {
  const [showUfo, setShowUfo] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    // 첫 등장: 45초 ~ 90초 후
    const scheduleUfo = () => {
      const randomDelay = Math.random() * 45000 + 45000;

      setTimeout(() => {
        setShowUfo(true);
        setTimeout(() => setIsAnimating(true), 100);
      }, randomDelay);
    };

    scheduleUfo();

    return () => {};
  }, []);

  // CSS 애니메이션 종료 후
  const handleAnimationEnd = () => {
    setIsAnimating(false);
    setShowUfo(false);

    // 다음 UFO: 90초 ~ 180초 후 (1.5분 ~ 3분)
    const nextDelay = Math.random() * 90000 + 90000;
    setTimeout(() => {
      setShowUfo(true);
      setTimeout(() => setIsAnimating(true), 100);
    }, nextDelay);
  };

  if (!showUfo) return null;

  return (
    <div
      className={`${styles.ufoContainer} ${isAnimating ? styles.flying : ""}`}
      onAnimationEnd={handleAnimationEnd}
    >
      <Canvas
        camera={{ position: [0, 1, 5], fov: 50 }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 5, 5]} intensity={1} />
        <pointLight position={[-5, 5, -5]} intensity={0.5} color="#88ff88" />

        <Suspense fallback={null}>
          <UfoModel />
        </Suspense>
      </Canvas>
    </div>
  );
}

// GLB 모델 프리로드
useGLTF.preload("/Flying saucer.glb");
