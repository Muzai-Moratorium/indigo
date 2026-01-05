"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./cctv.module.scss";
import ProtectedRoute from "../../../components/auth/ProtectedRoute";

function DetectorPage() {
  const router = useRouter();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [status, setStatus] = useState("Connecting...");
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [stream, setStream] = useState(null);
  const [fps, setFps] = useState(0);
  const [isMonitoring, setIsMonitoring] = useState(false);

  // 페이지 이탈 확인 (브라우저 새로고침/닫기)
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (isMonitoring) {
        e.preventDefault();
        e.returnValue = "";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isMonitoring]);

  // 모든 링크 클릭 가로채기 (사이드바 포함)
  useEffect(() => {
    const handleClick = (e) => {
      if (!isMonitoring) return;

      // a 태그 클릭인지 확인
      const link = e.target.closest("a");
      if (link && link.href) {
        const url = new URL(link.href);
        const currentPath = window.location.pathname;

        // 같은 페이지가 아닌 경우에만 확인
        if (url.pathname !== currentPath) {
          e.preventDefault();
          e.stopPropagation();

          const confirmed = window.confirm(
            "모니터링 중입니다!\n\n페이지를 떠나면 감시가 중단됩니다.\n정말 나가시겠습니까?"
          );

          if (confirmed) {
            setIsMonitoring(false);
            window.location.href = link.href;
          }
        }
      }
    };

    // 브라우저 뒤로가기/앞으로가기 가로채기
    const handlePopState = (e) => {
      if (isMonitoring) {
        const confirmed = window.confirm(
          "모니터링 중입니다!\n\n페이지를 떠나면 감시가 중단됩니다.\n정말 나가시겠습니까?"
        );

        if (!confirmed) {
          // 뒤로가기 취소 - 현재 페이지로 다시 push
          window.history.pushState(null, "", window.location.pathname);
        } else {
          setIsMonitoring(false);
        }
      }
    };

    // 현재 상태를 history에 push (뒤로가기 감지용)
    if (isMonitoring) {
      window.history.pushState(null, "", window.location.pathname);
    }

    document.addEventListener("click", handleClick, true);
    window.addEventListener("popstate", handlePopState);

    return () => {
      document.removeEventListener("click", handleClick, true);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [isMonitoring]);

  // 홈으로 돌아가기 버튼용
  const handleNavigateAway = (e, href) => {
    if (isMonitoring) {
      e.preventDefault();
      const confirmed = window.confirm(
        "모니터링 중입니다!\n\n페이지를 떠나면 감시가 중단됩니다.\n정말 나가시겠습니까?"
      );
      if (confirmed) {
        setIsMonitoring(false);
        router.push(href);
      }
    } else {
      router.push(href);
    }
  };

  useEffect(() => {
    async function getDevices() {
      try {
        const tempStream = await navigator.mediaDevices.getUserMedia({
          video: true,
        });
        tempStream.getTracks().forEach((track) => track.stop());

        const deviceList = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = deviceList.filter(
          (device) => device.kind === "videoinput"
        );
        setDevices(videoDevices);

        if (videoDevices.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(videoDevices[0].deviceId);
        }
      } catch (error) {
        console.error("카메라 접근 오류:", error);
      }
    }
    getDevices();
  }, []);

  useEffect(() => {
    if (!selectedDeviceId) return;

    // 정리할 리소스들을 저장
    let ws = null;
    let intervalId = null;
    let currentStream = null;

    // Binary WebSocket 연결
    ws = new WebSocket("ws://localhost:8000/security/ws");
    ws.binaryType = "arraybuffer";

    let frameCount = 0;
    let lastTime = Date.now();

    ws.onopen = () => {
      setStatus("Connected");
      setIsMonitoring(true);
      console.log("WebSocket 연결 성공");
    };

    ws.onclose = () => {
      setStatus("Disconnected");
      setIsMonitoring(false);
      console.log("WebSocket 연결 종료");
    };

    ws.onerror = (error) => {
      setStatus("Error");
      console.error("WebSocket 에러:", error);
    };

    ws.onmessage = (event) => {
      frameCount++;
      const now = Date.now();
      if (now - lastTime >= 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = now;
      }

      const data = JSON.parse(event.data);
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (data.predictions) {
        data.predictions.forEach((prediction) => {
          const [x1, y1, x2, y2] = prediction.box;
          const label = prediction.label;
          const score = prediction.score;

          ctx.strokeStyle = "#00FF00";
          ctx.lineWidth = 3;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

          ctx.fillStyle = "#00FF00";
          const text = `${label} ${score}`;
          const textWidth = ctx.measureText(text).width;
          ctx.fillRect(x1, y1 - 20, textWidth + 10, 20);

          ctx.fillStyle = "black";
          ctx.font = "16px Arial";
          ctx.fillText(text, x1 + 5, y1 - 5);
        });
      }
    };

    // 카메라 스트림 시작
    navigator.mediaDevices
      .getUserMedia({
        video: {
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
          width: { ideal: 640 },
          height: { ideal: 640 },
        },
      })
      .then((newStream) => {
        // 이전 스트림 정리
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
        }

        currentStream = newStream;
        setStream(newStream);

        if (videoRef.current) {
          videoRef.current.srcObject = newStream;
          videoRef.current.play();
        }

        const hiddenCanvas = document.createElement("canvas");
        const hiddenCtx = hiddenCanvas.getContext("2d");
        hiddenCanvas.width = 640;
        hiddenCanvas.height = 640;

        function sendFrame() {
          if (!videoRef.current || !hiddenCtx) return;

          if (ws && ws.readyState === WebSocket.OPEN) {
            hiddenCtx.drawImage(videoRef.current, 0, 0, 640, 640);

            hiddenCanvas.toBlob(
              (blob) => {
                if (blob && ws && ws.readyState === WebSocket.OPEN) {
                  blob.arrayBuffer().then((buffer) => {
                    ws.send(buffer);
                  });
                }
              },
              "image/jpeg",
              0.6
            );
          }
        }

        intervalId = setInterval(sendFrame, 150);
      })
      .catch((error) => {
        console.error("카메라 접근 실패:", error);
        setStatus("Camera Error");
      });

    // [핵심] Cleanup 함수: 페이지 이동 시 실행
    return () => {
      console.log("페이지 이동 - 리소스 정리 시작");

      // 1. interval 정리
      if (intervalId) {
        clearInterval(intervalId);
        console.log("  ✓ Frame 전송 interval 정리");
      }

      // 2. WebSocket 연결 종료
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        console.log("  ✓ WebSocket 연결 종료");
      }

      // 3. 카메라 스트림 정지
      if (currentStream) {
        currentStream.getTracks().forEach((track) => track.stop());
        console.log("  ✓ 카메라 스트림 정지");
      }

      console.log("리소스 정리 완료");
    };
  }, [selectedDeviceId]);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>CCTV</h1>

      <div className={styles.selectContainer}>
        <label className={styles.label}>카메라 선택:</label>
        <select
          value={selectedDeviceId}
          onChange={(e) => setSelectedDeviceId(e.target.value)}
          className={styles.select}
        >
          {devices.map((device, index) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || `카메라 ${index + 1}`}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.videoWrapper}>
        <div
          className={`${styles.statusOverlay} ${
            status === "Connected"
              ? styles.statusConnected
              : styles.statusDisconnected
          }`}
        >
          Status: {status} | FPS: {fps}
        </div>

        <video
          ref={videoRef}
          width={640}
          height={640}
          className={styles.videoElement}
          playsInline
          muted
        />

        <canvas
          ref={canvasRef}
          width={640}
          height={640}
          className={styles.canvasElement}
        />
      </div>

      <button
        onClick={(e) => handleNavigateAway(e, "/")}
        className={styles.backLink}
        style={{ background: "none", border: "none", cursor: "pointer" }}
      >
        ← 홈으로 돌아가기
      </button>
    </div>
  );
}

// ProtectedRoute로 감싸서 로그인 필수 페이지로 만듦
export default function ProtectedDetectorPage() {
  return (
    <ProtectedRoute>
      <DetectorPage />
    </ProtectedRoute>
  );
}
