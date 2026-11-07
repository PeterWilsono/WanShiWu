'use strict'

const { contextBridge, ipcRenderer } = require('electron')

// 只暴露数据位置相关的只读/受控能力，页面拿不到任意文件系统权限。
contextBridge.exposeInMainWorld('wanshiwuDesktop', {
  isDesktop: true,
  getDataLocation: () => ipcRenderer.invoke('wanshiwu:data-location'),
  chooseDataLocation: () => ipcRenderer.invoke('wanshiwu:choose-data-location'),
  openDataFolder: () => ipcRenderer.invoke('wanshiwu:open-data-folder'),
  openLegacyFolder: () => ipcRenderer.invoke('wanshiwu:open-legacy-folder'),
})
