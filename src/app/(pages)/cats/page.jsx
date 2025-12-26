"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import styles from "./page.module.scss";

export default function DetectorPage() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [status, setStatus] = useState("Connecting...");
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [stream, setStream] = useState(null);
  const [fps, setFps] = useState(0);

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

    // Binary WebSocket 연결
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");
    ws.binaryType = "arraybuffer"; // 중요: 바이너리 타입 설정

    let frameCount = 0;
    let lastTime = Date.now();

    ws.onopen = () => {
      setStatus("Connected");
      console.log("WebSocket Connected");
    };

    ws.onclose = () => {
      setStatus("Disconnected");
      console.log("WebSocket Disconnected");
    };

    ws.onerror = (error) => {
      setStatus("Error");
      console.error("WebSocket Error:", error);
    };

    ws.onmessage = (event) => {
      // FPS 계산
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

    navigator.mediaDevices
      .getUserMedia({
        video: {
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
          width: { ideal: 640 },
          height: { ideal: 640 },
        },
      })
      .then((newStream) => {
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
        }
        setStream(newStream);

        if (videoRef.current) {
          videoRef.current.srcObject = newStream;
          videoRef.current.play();
        }

        const hiddenCanvas = document.createElement("canvas");
        const hiddenCtx = hiddenCanvas.getContext("2d");
        hiddenCanvas.width = 640;
        hiddenCanvas.height = 640;

        async function sendFrame() {
          if (!videoRef.current || !hiddenCtx) return;

          if (ws.readyState === WebSocket.OPEN) {
            hiddenCtx.drawImage(videoRef.current, 0, 0, 640, 640);

            // Blob으로 변환 (비동기, 더 효율적)
            hiddenCanvas.toBlob(
              (blob) => {
                if (blob) {
                  // ArrayBuffer로 변환하여 전송
                  blob.arrayBuffer().then((buffer) => {
                    ws.send(buffer);
                  });
                }
              },
              "image/jpeg",
              0.6 // 품질 조정 가능
            );
          }
        }

        // 150ms마다 전송 (약 6-7 FPS)
        const intervalId = setInterval(sendFrame, 150);

        return () => {
          clearInterval(intervalId);
          ws.close();
        };
      });

    return () => {
      ws.close();
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [selectedDeviceId]);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>고양이 탐색기</h1>

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

      <Link href="/" className={styles.backLink}>
        ← Back to Home
      </Link>
    </div>
  );
}
