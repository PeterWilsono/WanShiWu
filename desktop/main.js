const { app, BrowserWindow, Menu, dialog, ipcMain, session, shell } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const net = require('node:net')
const path = require('node:path')
const affirmations = require('./affirmations.json')
const {
  ensureDataDirectory,
  hasDatabase,
  moveDataTo,
  resolveDataLocation,
  systemLocalRoot,
  writePointer,
} = require('./data-location')

const SMOKE_TEST = process.argv.includes('--smoke-test')
const CLOSE_TEST = process.argv.includes('--close-test')
let mainWindow = null
let backendProcess = null
let backendExited = false
let backendExitCode = null
let quitting = false
let restarting = false
let ready = false
let localOrigin = ''
let closeDialogOpen = false
let lastAffirmationIndex = -1
let dataLocation = null
let logDirectory = ''

function nextAffirmation() {
  let index = Math.floor(Math.random() * affirmations.length)
  if (affirmations.length > 1) {
    while (index === lastAffirmationIndex) index = Math.floor(Math.random() * affirmations.length)
  }
  lastAffirmationIndex = index
  return affirmations[index]
}

async function confirmClose(targetWindow) {
  if (closeDialogOpen) return
  closeDialogOpen = true
  const affirmation = nextAffirmation()
  if (CLOSE_TEST) console.log(`WANSHIWU_CLOSE_CONFIRM_SHOWN ${affirmation}`)
  const { response } = await dialog.showMessageBox(targetWindow, {
    type: 'question',
    title: '要暂时合上万事屋吗？',
    message: affirmation,
    detail: '您记录的内容会妥善保存在本机。准备好后，我们再继续。',
    buttons: ['再留一会儿', '安心关闭'],
    defaultId: 0,
    cancelId: 0,
    noLink: true,
  })
  closeDialogOpen = false
  if (CLOSE_TEST) console.log(`WANSHIWU_CLOSE_CONFIRM_RESPONSE ${response}`)
  if (response === 1) {
    quitting = true
    targetWindow.close()
  }
}

function backendExecutable() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'backend', 'wanshiwu-backend.exe')
    : path.join(__dirname, 'dist', 'backend', 'wanshiwu-backend', 'wanshiwu-backend.exe')
}

function applicationDirectory() {
  // 打包后 resources 的上级就是安装目录；开发时就是 desktop 目录。
  return app.isPackaged ? path.dirname(process.resourcesPath) : __dirname
}

/**
 * 启动前确定数据目录：设置过的位置 → 安装目录 data → 系统本地目录。
 * 若新位置还没有数据库而旧位置有，则先复制过来，避免换位置后看起来数据丢失。
 */
function bootstrapDataLocation() {
  const base = resolveDataLocation({ appDir: applicationDirectory() })
  const legacyDir = base.source === 'env' ? null : path.join(systemLocalRoot(), 'data')
  const ensured = ensureDataDirectory(base.dataDir, { legacyDir })
  dataLocation = {
    ...base,
    dataDir: ensured.dataDir,
    migrated: ensured.migrated === true,
    migrationError: ensured.error || null,
    usingLegacy: ensured.fallback === true,
  }
  logDirectory = path.join(dataLocation.dataDir, 'logs')
  if (dataLocation.migrated) {
    console.log(`WANSHIWU_DATA_MIGRATED ${legacyDir} -> ${dataLocation.dataDir}`)
  }
  if (dataLocation.migrationError) {
    console.error(`WANSHIWU_DATA_MIGRATION_FAILED ${dataLocation.migrationError}`)
  }
  return dataLocation
}

function prepareLog() {
  const directory = process.env.WANSHIWU_LOG_DIR || logDirectory || path.join(app.getPath('userData'), 'logs')
  fs.mkdirSync(directory, { recursive: true })
  const file = path.join(directory, 'backend.log')
  const previous = path.join(directory, 'backend.previous.log')
  if (fs.existsSync(file) && fs.statSync(file).size > 2 * 1024 * 1024) {
    fs.copyFileSync(file, previous)
  }
  return { file, stream: fs.createWriteStream(file, { flags: 'w' }) }
}

function portAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.unref()
    server.once('error', () => resolve(false))
    server.listen(port, '127.0.0.1', () => server.close(() => resolve(true)))
  })
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : 0
      server.close(() => port ? resolve(port) : reject(new Error('没有可用的本机端口')))
    })
  })
}

async function choosePort() {
  const configured = Number(process.env.WANSHIWU_PORT)
  if (Number.isInteger(configured) && configured > 0 && configured < 65536) return configured
  return (await portAvailable(8765)) ? 8765 : freePort()
}

function stopBackend() {
  if (!backendProcess || backendExited) return
  const pid = backendProcess.pid
  if (process.platform === 'win32' && pid) {
    spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' })
  } else {
    backendProcess.kill('SIGTERM')
  }
}

function stopBackendAndWait(timeoutMs = 8000) {
  return new Promise((resolve) => {
    if (!backendProcess || backendExited) {
      resolve()
      return
    }
    const timer = setTimeout(resolve, timeoutMs)
    backendProcess.once('exit', () => {
      clearTimeout(timer)
      resolve()
    })
    stopBackend()
  })
}

function dataLocationSummary() {
  const legacyDir = path.join(systemLocalRoot(), 'data')
  return {
    dataDir: dataLocation.dataDir,
    installDir: dataLocation.installDir,
    fallbackDir: dataLocation.fallbackDir,
    defaultDir: dataLocation.installDir,
    source: dataLocation.source,
    reason: dataLocation.reason,
    pointerFile: dataLocation.pointerFile,
    logFile: path.join(logDirectory, 'backend.log'),
    legacyDir,
    legacyHasData: legacyDir !== dataLocation.dataDir && hasDatabase(legacyDir),
    migrated: dataLocation.migrated,
    migrationError: dataLocation.migrationError,
    usingLegacy: dataLocation.usingLegacy,
    systemDrive: process.env.SystemDrive || 'C:',
    platform: process.platform,
    version: app.getVersion(),
  }
}

async function restartLater() {
  restarting = true
  setTimeout(() => {
    app.relaunch()
    app.exit(0)
  }, 700)
}

function registerIpc() {
  ipcMain.handle('wanshiwu:data-location', () => dataLocationSummary())

  ipcMain.handle('wanshiwu:open-data-folder', async () => {
    const error = await shell.openPath(dataLocation.dataDir)
    return { ok: !error, message: error || '' }
  })

  ipcMain.handle('wanshiwu:choose-data-location', async (event) => {
    const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow
    const picked = await dialog.showOpenDialog(targetWindow, {
      title: '选择万事屋数据保存位置',
      buttonLabel: '使用这个文件夹',
      defaultPath: dataLocation.dataDir,
      properties: ['openDirectory', 'createDirectory'],
    })
    if (picked.canceled || !picked.filePaths[0]) return { ok: false, canceled: true }

    const target = path.resolve(picked.filePaths[0])
    const current = path.resolve(dataLocation.dataDir)
    if (target === current) return { ok: false, message: '这就是当前使用的文件夹' }
    if (target.startsWith(`${current}${path.sep}`)) {
      return { ok: false, message: '不能在当前数据文件夹内部再建一层' }
    }

    const targetHasData = hasDatabase(target)

    const { response } = await dialog.showMessageBox(targetWindow, {
      type: 'question',
      title: '更换数据保存位置',
      message: targetHasData ? '这个文件夹里已经有万事屋数据' : '要把数据搬到这个文件夹吗？',
      detail: targetHasData
        ? `位置：${target}\n\n切换后会直接使用这里的现有数据，当前数据仍原样保留在原位置。软件需要重启。`
        : `新位置：${target}\n\n当前数据会完整复制过去并校验大小，之后以新位置为准。软件会自动重启。`,
      buttons: targetHasData ? ['使用这里的已有数据', '取消'] : ['开始迁移并重启', '取消'],
      defaultId: 0,
      cancelId: 1,
      noLink: true,
    })
    if (response !== 0) return { ok: false, canceled: true }

    if (!targetHasData) {
      await stopBackendAndWait()
      const result = moveDataTo(target, { sourceDir: current })
      if (!result.ok) return { ok: false, message: result.message }
    }

    try {
      writePointer(dataLocation.pointerFile, target)
    } catch (error) {
      return { ok: false, message: `无法保存新位置设置：${error.message}` }
    }

    await restartLater()
    return { ok: true, restarting: true, dataDir: target }
  })

  ipcMain.handle('wanshiwu:open-legacy-folder', async () => {
    const legacy = path.join(systemLocalRoot(), 'data')
    const error = await shell.openPath(legacy)
    return { ok: !error, message: error || '' }
  })
}

async function waitUntilHealthy() {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    if (backendExited) throw new Error(`本地服务提前退出（代码 ${backendExitCode ?? '未知'}）`)
    try {
      const response = await fetch(`${localOrigin}/api/v1/health`, {
        signal: AbortSignal.timeout(1500),
      })
      if (response.ok) {
        const body = await response.json()
        if (body?.data?.status === 'ok') return
      }
    } catch {
      // 数据库首次迁移期间服务尚未监听，继续等待。
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('等待本地服务启动超时')
}

async function startBackend() {
  const executable = backendExecutable()
  if (!fs.existsSync(executable)) throw new Error(`缺少内嵌运行组件：${executable}`)

  const port = await choosePort()
  localOrigin = `http://127.0.0.1:${port}`
  backendExited = false
  backendExitCode = null
  const log = prepareLog()
  backendProcess = spawn(executable, [], {
    env: {
      ...process.env,
      WANSHIWU_PORT: String(port),
      WANSHIWU_DATA_DIR: dataLocation.dataDir,
      WANSHIWU_LOG_DIR: logDirectory,
    },
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  backendProcess.stdout.on('data', (chunk) => log.stream.write(chunk))
  backendProcess.stderr.on('data', (chunk) => log.stream.write(chunk))
  backendProcess.once('error', (error) => {
    backendExited = true
    backendExitCode = error.code
  })
  backendProcess.once('exit', (code) => {
    backendExited = true
    backendExitCode = code
    if (!quitting && !restarting && ready) {
      dialog.showErrorBox('万事屋本地服务已停止', `请重新打开软件。\n运行日志：${log.file}`)
      app.quit()
    }
  })
  backendProcess.once('close', () => log.stream.end())
  await waitUntilHealthy()
  return log.file
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 1024,
    minHeight: 700,
    show: true,
    backgroundColor: '#f4f1e9',
    autoHideMenuBar: true,
    title: '万事屋',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  })
  mainWindow.loadFile(path.join(__dirname, 'loading.html'))
  mainWindow.on('close', (event) => {
    if (quitting || SMOKE_TEST) return
    event.preventDefault()
    void confirmClose(mainWindow)
  })
  mainWindow.on('closed', () => { mainWindow = null })
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url)
    return { action: 'deny' }
  })
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (localOrigin && url.startsWith(localOrigin)) return
    event.preventDefault()
    if (/^https?:\/\//.test(url)) shell.openExternal(url)
  })
}

async function openApplication() {
  const logFile = await startBackend()
  if (quitting) return logFile
  if (!mainWindow) createWindow()
  // 桌面资源已随软件内置，不需要 PWA；清理旧版缓存但保留 localStorage 登录态。
  await session.defaultSession.clearStorageData({
    origin: localOrigin,
    storages: ['serviceworkers', 'cachestorage'],
  })
  await mainWindow.loadURL(localOrigin)
  ready = true
  mainWindow.show()
  if (SMOKE_TEST) {
    console.log(`WANSHIWU_DESKTOP_SMOKE_OK ${localOrigin}`)
    setTimeout(() => app.quit(), 300)
  }
  if (CLOSE_TEST) {
    console.log('WANSHIWU_CLOSE_CONFIRM_READY')
    setTimeout(() => mainWindow?.close(), 300)
  }
  return logFile
}

async function startWithRecovery() {
  try {
    if (!dataLocation) {
      bootstrapDataLocation()
      registerIpc()
    }
    if (SMOKE_TEST) {
      console.log(`WANSHIWU_DESKTOP_DATA_DIR ${dataLocation.dataDir} (${dataLocation.source})`)
    }
    await openApplication()
  } catch (error) {
    if (quitting) return
    stopBackend()
    const detail = error instanceof Error ? error.message : String(error)
    if (SMOKE_TEST) {
      console.error(`WANSHIWU_DESKTOP_SMOKE_FAILED ${detail}`)
      app.exit(1)
      return
    }
    const logFile = path.join(logDirectory || path.join(app.getPath('userData'), 'logs'), 'backend.log')
    const { response } = await dialog.showMessageBox({
      type: 'error',
      title: '万事屋暂时未能启动',
      message: '万事屋暂时未能启动',
      detail: `${detail}\n\n可以点击“重试”。若仍失败，请把日志发给软件提供者：\n${logFile}`,
      buttons: ['重试', '退出'],
      defaultId: 0,
      cancelId: 1,
    })
    if (response === 0) await startWithRecovery()
    else app.quit()
  }
}

Menu.setApplicationMenu(null)
// 应用页面只来自本机回环地址，必须绕过系统/环境代理，否则后端正常也会 ERR_FAILED。
app.commandLine.appendSwitch('no-proxy-server')
app.disableHardwareAcceleration()
app.setName('万事屋')
// 仅用于自动化验收：打印解析结果后立即退出，不启动本地服务。
if (process.argv.includes('--probe-data-location')) {
  bootstrapDataLocation()
  console.log(`WANSHIWU_DATA_LOCATION ${JSON.stringify(dataLocationSummary())}`)
  app.exit(0)
  return
}
const hasSingleInstance = app.requestSingleInstanceLock()
if (!hasSingleInstance) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
  app.on('before-quit', () => {
    quitting = true
    stopBackend()
  })
  app.on('window-all-closed', () => app.quit())
  app.whenReady().then(startWithRecovery)
}
