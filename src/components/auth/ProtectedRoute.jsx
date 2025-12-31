"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  // 로딩 중일 때
  if (loading) {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>로딩 중...</p>
      </div>
    );
  }

  // 로그인 안됐으면 null (리다이렉트 중)
  if (!user) {
    return null;
  }

  // 로그인 됐으면 children 렌더링
  return <>{children}</>;
}
