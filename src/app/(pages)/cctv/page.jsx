"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
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

  // 모델 선택 상태
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [isModelSwitching, setIsModelSwitching] = useState(false);

  // MediaPipe 설정 상태
  const [mediapipeEnabled, setMediapipeEnabled] = useState(true);
  const [mediapipeInterval, setMediapipeInterval] = useState(5);
  const [mediapipeAvailable, setMediapipeAvailable] = useState(false);

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

  // MediaPipe 설정 조회
  useEffect(() => {
    async function fetchMediapipeSettings() {
      try {
        const response = await fetch(
          "http://localhost:8000/security/mediapipe/settings"
        );
        if (response.ok) {
          const data = await response.json();
          setMediapipeEnabled(data.enabled);
          setMediapipeInterval(data.frameInterval);
          setMediapipeAvailable(data.available);
        }
      } catch (error) {
        console.error("MediaPipe 설정 조회 실패:", error);
      }
    }
    fetchMediapipeSettings();
  }, []);

  // MediaPipe 토글 핸들러
  const handleMediapipeToggle = async () => {
    const newValue = !mediapipeEnabled;
    try {
      const response = await fetch(
        `http://localhost:8000/security/mediapipe/toggle?enabled=${newValue}`,
        { method: "POST" }
      );
      if (response.ok) {
        setMediapipeEnabled(newValue);
        console.log("MediaPipe:", newValue ? "ON" : "OFF");
      }
    } catch (error) {
      console.error("MediaPipe 토글 실패:", error);
    }
  };

  // MediaPipe 주기 변경 핸들러
  const handleMediapipeIntervalChange = async (interval) => {
    const value = parseInt(interval);
    if (isNaN(value) || value < 1 || value > 30) return;

    try {
      const response = await fetch(
        `http://localhost:8000/security/mediapipe/interval?interval=${value}`,
        { method: "POST" }
      );
      if (response.ok) {
        setMediapipeInterval(value);
        console.log("MediaPipe 주기:", value);
      }
    } catch (error) {
      console.error("MediaPipe 주기 변경 실패:", error);
    }
  };

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

      // MediaPipe Pose 33 키포인트 스켈레톤 연결 (0-indexed)
      // 0: 코, 1-4: 눈/눈썹, 5-8: 귀, 9-10: 입, 11-12: 어깨
      // 13-14: 팔꿈치, 15-16: 손목, 17-22: 손가락, 23-24: 엉덩이
      // 25-26: 무릎, 27-28: 발목, 29-32: 발
      const SKELETON = [
        // 몸통
        [11, 12], // 어깨
        [11, 23],
        [12, 24], // 어깨-엉덩이
        [23, 24], // 엉덩이
        // 왼팔
        [11, 13],
        [13, 15], // 어깨-팔꿈치-손목
        // 오른팔
        [12, 14],
        [14, 16],
        // 왼다리
        [23, 25],
        [25, 27], // 엉덩이-무릎-발목
        // 오른다리
        [24, 26],
        [26, 28],
        // 얼굴
        [0, 1],
        [0, 4], // 코-눈
        [1, 2],
        [4, 5], // 눈
        [2, 3],
        [5, 6], // 눈-귀
      ];

      if (data.predictions) {
        // 320x320 모델 출력 → 640x640 캔버스 스케일
        const SCALE = 2;

        data.predictions.forEach((prediction) => {
          const [bx1, by1, bx2, by2] = prediction.box;
          // 스케일 적용
          const x1 = bx1 * SCALE;
          const y1 = by1 * SCALE;
          const x2 = bx2 * SCALE;
          const y2 = by2 * SCALE;
          const label = prediction.label;
          const score = prediction.score;

          // 클래스별 색상/스타일 결정 (화재/연기는 빨간색 강조)
          const isDanger = label === "fire" || label === "smoke";
          const color = isDanger ? "#FF0000" : "#00FF00";
          const lineWidth = isDanger ? 4 : 2;

          // 박스 그리기
          ctx.strokeStyle = color;
          ctx.lineWidth = lineWidth;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

          // 라벨을 박스 안쪽 상단에 표시
          ctx.font = "bold 14px Arial";
          const text = `${label} ${(score * 100).toFixed(0)}%`;
          const textWidth = ctx.measureText(text).width;

          // 라벨 배경
          ctx.fillStyle = color;
          ctx.fillRect(x1, y1, textWidth + 8, 20);

          // 라벨 텍스트
          ctx.fillStyle = isDanger ? "white" : "black";
          ctx.fillText(text, x1 + 4, y1 + 15);

          // 키포인트 그리기 (MediaPipe Pose 33개)
          if (prediction.keypoints && prediction.keypoints.length >= 25) {
            const kpts = prediction.keypoints;

            // 스켈레톤 연결선 그리기
            ctx.strokeStyle = "#00FFFF";
            ctx.lineWidth = 2;
            SKELETON.forEach(([i, j]) => {
              if (i < kpts.length && j < kpts.length) {
                const [x1k, y1k, c1] = kpts[i];
                const [x2k, y2k, c2] = kpts[j];
                if (c1 > 0.3 && c2 > 0.3) {
                  ctx.beginPath();
                  ctx.moveTo(x1k * SCALE, y1k * SCALE);
                  ctx.lineTo(x2k * SCALE, y2k * SCALE);
                  ctx.stroke();
                }
              }
            });

            // 키포인트 점 그리기 (주요 관절만)
            const mainJoints = [
              0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
            ];
            mainJoints.forEach((idx) => {
              if (idx < kpts.length) {
                const [kx, ky, kconf] = kpts[idx];
                if (kconf > 0.3) {
                  // 부위별 색상
                  let pointColor = "#FF00FF"; // 기본: 분홍
                  if (idx <= 10) pointColor = "#FFFF00"; // 얼굴/어깨: 노랑
                  else if (idx <= 22) pointColor = "#00FF00"; // 팔/손: 초록
                  else pointColor = "#FF6600"; // 다리/발: 주황

                  ctx.fillStyle = pointColor;
                  ctx.beginPath();
                  ctx.arc(kx * SCALE, ky * SCALE, 4, 0, Math.PI * 2);
                  ctx.fill();
                }
              }
            });
          }
        });
      }

      // 알림(alerts) 표시 - 이상행동, 배회자, 화재 등
      if (data.alerts && data.alerts.length > 0) {
        data.alerts.forEach((alert) => {
          // 320x320 좌표를 640x640으로 스케일
          const ALERT_SCALE = 2;
          const [ax1, ay1, ax2, ay2] = alert.box;
          const x1 = ax1 * ALERT_SCALE;
          const y1 = ay1 * ALERT_SCALE;
          const x2 = ax2 * ALERT_SCALE;
          const y2 = ay2 * ALERT_SCALE;

          // 알림 유형별 스타일
          let alertColor = "#FF0000";
          let alertText = "";

          if (alert.type === "abnormal") {
            alertColor = "#FF00FF"; // 마젠타
            const behaviors = alert.behaviors || [];
            const behaviorLabels = {
              FALL: "넘어짐!",
              HANDS_UP: "손들기!",
              FAST_MOTION: "빠른동작!",
            };
            alertText = behaviors.map((b) => behaviorLabels[b] || b).join(" ");
          } else if (alert.type === "loitering") {
            alertColor = "#FFA500"; // 주황
            alertText = "배회자 감지!";
          } else if (alert.type === "fire" || alert.type === "smoke") {
            alertColor = "#FF0000";
            alertText = alert.type === "fire" ? "화재!" : "연기!";
          }

          // 경고 박스 (깜빡이는 효과)
          ctx.strokeStyle = alertColor;
          ctx.lineWidth = 4;
          ctx.setLineDash([10, 5]);
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.setLineDash([]);

          // 경고 라벨 (상단)
          ctx.font = "bold 16px Arial";
          const textWidth = ctx.measureText(alertText).width;
          ctx.fillStyle = alertColor;
          ctx.fillRect(x1, y1 - 28, textWidth + 12, 26);
          ctx.fillStyle = "white";
          ctx.fillText(alertText, x1 + 6, y1 - 10);
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
        hiddenCanvas.width = 320; // 640 → 320 (속도 향상)
        hiddenCanvas.height = 320;

        let isSending = false; // 프레임 전송 중 플래그

        function sendFrame() {
          if (!videoRef.current || !hiddenCtx) return;
          if (isSending) return; // 이전 프레임 전송 중이면 스킵

          if (ws && ws.readyState === WebSocket.OPEN) {
            isSending = true;
            hiddenCtx.drawImage(videoRef.current, 0, 0, 320, 320);

            hiddenCanvas.toBlob(
              (blob) => {
                if (blob && ws && ws.readyState === WebSocket.OPEN) {
                  blob.arrayBuffer().then((buffer) => {
                    ws.send(buffer);
                    isSending = false; // 전송 완료
                  });
                } else {
                  isSending = false;
                }
              },
              "image/jpeg",
              0.7 // 품질 약간 높임
            );
          }
        }

        intervalId = setInterval(sendFrame, 33); // 약 30 FPS
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
        <label className={styles.label}>카메라 선택</label>
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
      {/* MediaPipe 설정 (관절 추출) */}
      <div className={`${styles.selectContainer} ${styles.mediapipeSection}`}>
        <div className={styles.mediapipeControls}>
          <label className={styles.label}>MediaPipe</label>
          <button
            onClick={handleMediapipeToggle}
            disabled={!mediapipeAvailable}
            className={mediapipeEnabled ? styles.isEnabled : ""}
          >
            {mediapipeEnabled ? "ON" : "OFF"}
          </button>
          {!mediapipeAvailable && (
            <span className={styles.noModelWarning}>(모델 없음)</span>
          )}
        </div>

        {mediapipeEnabled && mediapipeAvailable && (
          <div className={styles.mediapipeControls}>
            <select
              value={mediapipeInterval}
              onChange={(e) => handleMediapipeIntervalChange(e.target.value)}
              className={`${styles.select} ${styles.intervalSelect}`}
            >
              <option value="1">1FPS</option>
              <option value="3">3FPS</option>
              <option value="5">5FPS</option>
              <option value="10">10FPS</option>
              <option value="15">15FPS</option>
              <option value="30">30FPS</option>
            </select>
          </div>
        )}
      </div>

      <div className={styles.videoWrapper}>
        <div
          className={`${styles.statusOverlay} ${
            status === "Connected"
              ? styles.statusConnected
              : styles.statusDisconnected
          }`}
        >
          상태: {status} | : {fps}
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
