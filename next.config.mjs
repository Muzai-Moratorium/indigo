/** @type {import('next').NextConfig} */

// Electron 프로덕션 빌드에서만 static export 사용
const isElectronBuild = process.env.ELECTRON_BUILD === "true";

const nextConfig = {
  // Electron 빌드 시에만 정적 export
  ...(isElectronBuild && {
    output: "export",
    trailingSlash: true,
    // Electron에서 상대 경로로 로드
    assetPrefix: "./",
  }),
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
