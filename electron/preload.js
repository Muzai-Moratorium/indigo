const { contextBridge, ipcRenderer } = require("electron");

// 보안을 위해 필요한 API만 노출
contextBridge.exposeInMainWorld("electronAPI", {
  // 앱 정보
  getAppInfo: () => ({
    isElectron: true,
    version: require("../package.json").version,
  }),

  // IPC 통신 (추후 필요시 확장)
  send: (channel, data) => {
    const validChannels = ["app-event"];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },

  receive: (channel, callback) => {
    const validChannels = ["app-response"];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => callback(...args));
    }
  },
});

console.log("[Preload] Electron API 노출 완료");
