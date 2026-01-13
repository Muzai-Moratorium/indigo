"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import { useRouter } from "next/navigation";
import styles from "./mypage.module.scss";
import { TiRefreshOutline } from "react-icons/ti";

export default function MyPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [personName, setPersonName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [whitelist, setWhitelist] = useState([]);

  // 카카오 연동 상태
  const [kakaoStatus, setKakaoStatus] = useState({
    connected: false,
    message: "확인 중...",
  });

  // 카메라 관련 상태
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [stream, setStream] = useState(null);

  // 화이트리스트 조회
  const fetchWhitelist = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/security/whitelist");
      const data = await res.json();
      setWhitelist(data.names || []);
    } catch (err) {
      console.error("화이트리스트 조회 실패:", err);
    }
  }, []);

  // 카카오 연동 상태 확인
  const fetchKakaoStatus = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/kakao/status");
      const data = await res.json();
      setKakaoStatus(data);
    } catch (err) {
      setKakaoStatus({ connected: false, message: "서버 연결 실패" });
    }
  }, []);

  // 카카오 로그인 페이지로 이동
  const handleKakaoLogin = () => {
    window.location.href = "http://localhost:8000/kakao/login";
  };

  // 컴포넌트 마운트 시 조회
  useEffect(() => {
    if (user) {
      fetchWhitelist();
      fetchKakaoStatus();
    }
  }, [user, fetchWhitelist, fetchKakaoStatus]);

  // 로그인 체크 - 로딩이 끝난 후에만 체크
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  // 카메라 정리
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [stream]);

  // 로딩 중이거나 로그인되지 않았으면 렌더링 안함
  if (authLoading || !user) {
    return <div className={styles.container}>로딩 중...</div>;
  }

  // 파일 선택 핸들러
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
      // 카메라 닫기
      closeCamera();
    }
  };

  // 카메라 열기
  const openCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
      });
      setStream(mediaStream);
      setIsCameraOpen(true);

      // 비디오 요소에 스트림 연결
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      }, 100);
    } catch (err) {
      setMessage("카메라를 열 수 없습니다: " + err.message);
    }
  };

  // 카메라 닫기
  const closeCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setIsCameraOpen(false);
  };

  // 사진 촬영
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    // 캔버스를 Blob으로 변환
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], "camera_capture.jpg", {
            type: "image/jpeg",
          });
          setSelectedFile(file);
          setPreview(canvas.toDataURL("image/jpeg"));
          closeCamera();
        }
      },
      "image/jpeg",
      0.9
    );
  };

  // 얼굴 등록 핸들러
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedFile || !personName.trim()) {
      setMessage("이름과 사진을 모두 입력해주세요.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("name", personName.trim());

      const response = await fetch(
        "http://localhost:8000/security/whitelist/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (response.ok) {
        setMessage("얼굴 등록 완료!");
        setSelectedFile(null);
        setPreview(null);
        setPersonName("");
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        fetchWhitelist();
      } else {
        setMessage(`${data.detail || "등록 실패"}`);
      }
    } catch (err) {
      setMessage(`오류: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>마이페이지</h1>

        {/* 유저 정보 */}
        <section className={styles.section}>
          <h2>내 정보</h2>
          <p>이메일: {user?.email || "로딩 중..."}</p>
        </section>

        {/* 카카오 연동 */}
        <section className={styles.section}>
          <h2>카카오톡 알림 연동</h2>
          <p className={styles.description}>
            배회자 감지 시 카카오톡으로 알림을 받을 수 있습니다.
          </p>
          <div className={styles.kakaoStatus}>
            <span
              className={
                kakaoStatus.connected ? styles.connected : styles.disconnected
              }
            >
              {kakaoStatus.connected ? "연동됨" : "연동 안됨"}
            </span>
            {!kakaoStatus.connected && (
              <button
                type="button"
                onClick={handleKakaoLogin}
                className={styles.kakaoBtn}
              >
                <img src="kakao_login_large_narrow.png" alt="" />
              </button>
            )}
            {kakaoStatus.connected && (
              <>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await fetch("http://localhost:8000/kakao/logout", {
                        method: "POST",
                      });
                      fetchKakaoStatus(); // 상태 새로고침
                    } catch (err) {
                      console.error("로그아웃 실패:", err);
                    }
                  }}
                  className={styles.logoutBtn}
                >
                  연동 해제
                </button>
                <button
                  type="button"
                  onClick={fetchKakaoStatus}
                  className={styles.refreshBtn}
                >
                  <TiRefreshOutline />
                </button>
              </>
            )}
          </div>
        </section>

        {/* 얼굴 등록 */}
        <section className={styles.section}>
          <h2>가족 얼굴 등록</h2>
          <p className={styles.description}>
            등록된 가족은 배회자로 감지되지 않습니다.
          </p>

          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="personName">이름</label>
              <input
                type="text"
                id="personName"
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
                placeholder="예: 홍길동"
              />
            </div>

            {/* 카메라 / 파일 선택 버튼 */}
            <div className={styles.captureButtons}>
              <button
                type="button"
                onClick={isCameraOpen ? closeCamera : openCamera}
                className={styles.cameraBtn}
              >
                {isCameraOpen ? "카메라 닫기" : "카메라로 촬영"}
              </button>
              <span>또는</span>
              <input
                type="file"
                id="faceImage"
                ref={fileInputRef}
                accept="image/*"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={styles.uploadBtn}
              >
                사진 업로드
              </button>
            </div>

            {/* 카메라 뷰 */}
            {isCameraOpen && (
              <div className={styles.cameraContainer}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={styles.cameraVideo}
                />
                <button
                  type="button"
                  onClick={capturePhoto}
                  className={styles.captureBtn}
                >
                  촬영하기
                </button>
              </div>
            )}
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {/* 미리보기 */}
            {preview && (
              <div className={styles.preview}>
                <img src={preview} alt="미리보기" />
                <button
                  type="button"
                  onClick={() => {
                    setPreview(null);
                    setSelectedFile(null);
                  }}
                  className={styles.clearBtn}
                >
                  ✕ 삭제
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !selectedFile || !personName.trim()}
              className={styles.submitBtn}
            >
              {loading ? "등록 중..." : "등록하기"}
            </button>

            {message && <p className={styles.message}>{message}</p>}
          </form>
        </section>

        {/* 등록된 가족 목록 */}
        <section className={styles.section}>
          <h2>등록된 가족</h2>
          {whitelist.length > 0 ? (
            <ul className={styles.whitelistNames}>
              {whitelist.map((name, idx) => (
                <li key={idx}>
                  <span>{name}</span>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!confirm(`'${name}'을(를) 삭제하시겠습니까?`)) return;
                      try {
                        const res = await fetch(
                          `http://localhost:8000/security/whitelist/${encodeURIComponent(
                            name
                          )}`,
                          {
                            method: "DELETE",
                          }
                        );
                        if (res.ok) {
                          setMessage(`'${name}' 삭제 완료`);
                          fetchWhitelist();
                        } else {
                          const data = await res.json();
                          setMessage(`❌ ${data.detail || "삭제 실패"}`);
                        }
                      } catch (err) {
                        setMessage(`오류: ${err.message}`);
                      }
                    }}
                    className={styles.deleteBtn}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>등록된 가족이 없습니다.</p>
          )}
        </section>
      </div>
    </div>
  );
}
