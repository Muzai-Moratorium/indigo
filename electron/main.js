const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow;
let backendProcess = null;

// 개발 모드 여부 확인
const isDev = !app.isPackaged;

// 백엔드 서버 시작
function startBackend() {
  return new Promise((resolve, reject) => {
    if (isDev) {
      // 개발 모드: uvicorn 직접 실행 (이미 실행 중이라면 스킵)
      console.log(
        "[Backend] 개발 모드 - 백엔드가 별도로 실행 중이라고 가정합니다."
      );
      resolve();
      return;
    }

    // 프로덕션 모드: 패키징된 백엔드 실행
    const backendPath = path.join(
      process.resourcesPath,
      "backend",
      "backend.exe"
    );
    console.log("[Backend] 백엔드 시작:", backendPath);

    backendProcess = spawn(backendPath, [], {
      stdio: ["ignore", "pipe", "pipe"],
      detached: false,
    });

    backendProcess.stdout.on("data", (data) => {
      console.log("[Backend]", data.toString());
      if (data.toString().includes("Application startup complete")) {
        resolve();
      }
    });

    backendProcess.stderr.on("data", (data) => {
      console.error("[Backend Error]", data.toString());
    });

    backendProcess.on("error", (err) => {
      console.error("[Backend] 실행 실패:", err);
      reject(err);
    });

    // 5초 후에도 시작되지 않으면 타임아웃
    setTimeout(() => resolve(), 5000);
  });
}

// 백엔드 서버 종료
function stopBackend() {
  if (backendProcess) {
    console.log("[Backend] 백엔드 종료 중...");
    backendProcess.kill();
    backendProcess = null;
  }
}

// 메인 윈도우 생성
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
    icon: path.join(__dirname, "..", "public", "icon.ico"),
    title: "Cat App - Guardian Home Protection",
    show: false, // 준비될 때까지 숨김
  });

  // 개발 모드: localhost, 프로덕션: 빌드된 파일
  if (isDev) {
    mainWindow.loadURL("http://localhost:3000");
    mainWindow.webContents.openDevTools();
  } else {
    const outDir = path.join(__dirname, "..", "out");
    mainWindow.loadFile(path.join(outDir, "index.html"));

    // 프로덕션 모드: 네비게이션 인터셉트하여 로컬 파일로 라우팅
    mainWindow.webContents.on("will-navigate", (event, url) => {
      event.preventDefault();

      // URL에서 경로 추출
      let pagePath = url;

      // file:// 프로토콜 처리
      if (url.startsWith("file://")) {
        pagePath = url.replace(/^file:\/\//, "");
      }

      // http://localhost 또는 상대 경로 처리
      if (url.includes("localhost") || url.startsWith("/")) {
        const urlObj = new URL(url, "http://localhost");
        pagePath = urlObj.pathname;
      }

      // 경로 정규화 (앞뒤 슬래시 처리)
      pagePath = pagePath.replace(/^\//, "").replace(/\/$/, "");

      // 빈 경로는 index
      if (!pagePath || pagePath === "") {
        pagePath = "index";
      }

      // HTML 파일 경로 구성
      let htmlPath = path.join(outDir, pagePath, "index.html");

      // 파일이 없으면 직접 경로 시도
      const fs = require("fs");
      if (!fs.existsSync(htmlPath)) {
        htmlPath = path.join(outDir, pagePath + ".html");
      }
      if (!fs.existsSync(htmlPath)) {
        htmlPath = path.join(outDir, "index.html");
      }

      console.log("[Navigation]", url, "->", htmlPath);
      mainWindow.loadFile(htmlPath);
    });
  }

  // 준비되면 윈도우 표시
  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// 앱 시작
app.whenReady().then(async () => {
  console.log("[App] Cat App 시작 중...");

  try {
    await startBackend();
    console.log("[App] 백엔드 준비 완료");
  } catch (err) {
    console.error("[App] 백엔드 시작 실패:", err);
  }

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 모든 윈도우 닫힐 때
app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// 앱 종료 전 정리
app.on("before-quit", () => {
  stopBackend();
});
