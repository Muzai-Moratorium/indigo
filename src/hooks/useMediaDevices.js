"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * useMediaDevices - 미디어 장치(카메라/마이크) 관리 훅
 *
 * [사용 예시]
 * const { devices, selectedDevice, selectDevice, stream, startStream, stopStream } = useMediaDevices();
 *
 * [제공 기능]
 * 1. 사용 가능한 비디오 장치 목록 조회
 * 2. 장치 선택 및 스트림 시작/중지
 * 3. 컴포넌트 언마운트 시 자동 정리
 *
 * @param {Object} options - 스트림 옵션 { width, height }
 * @returns {Object} { devices, selectedDevice, selectDevice, stream, startStream, stopStream, error }
 */
export function useMediaDevices(options = { width: 640, height: 640 }) {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);

  // 장치 목록 조회
  const fetchDevices = useCallback(async () => {
    try {
      // 권한 획득을 위해 임시 스트림 요청
      const tempStream = await navigator.mediaDevices.getUserMedia({
        video: true,
      });
      tempStream.getTracks().forEach((track) => track.stop());

      // 장치 목록 조회
      const deviceList = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = deviceList.filter(
        (device) => device.kind === "videoinput"
      );
      setDevices(videoDevices);

      // 첫 번째 장치 자동 선택
      if (videoDevices.length > 0 && !selectedDevice) {
        setSelectedDevice(videoDevices[0].deviceId);
      }
    } catch (err) {
      console.error("카메라 접근 오류:", err);
      setError(err.message);
    }
  }, [selectedDevice]);

  // 스트림 시작
  const startStream = useCallback(
    async (deviceId) => {
      try {
        // 기존 스트림 정리
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
        }

        const newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            width: { ideal: options.width },
            height: { ideal: options.height },
          },
        });

        setStream(newStream);
        setError(null);
        return newStream;
      } catch (err) {
        console.error("스트림 시작 실패:", err);
        setError(err.message);
        return null;
      }
    },
    [stream, options.width, options.height]
  );

  // 스트림 중지
  const stopStream = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  }, [stream]);

  // 장치 선택
  const selectDevice = useCallback((deviceId) => {
    setSelectedDevice(deviceId);
  }, []);

  // 초기 장치 목록 로드
  useEffect(() => {
    fetchDevices();
  }, []);

  // 컴포넌트 언마운트 시 스트림 정리
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [stream]);

  return {
    devices,
    selectedDevice,
    selectDevice,
    stream,
    startStream,
    stopStream,
    error,
    refetch: fetchDevices,
  };
}

export default useMediaDevices;
