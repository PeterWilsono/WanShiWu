const { app, BrowserWindow, Menu, dialog, session, shell } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const net = require('node:net')
const path = require('node:path')

const SMOKE_TEST = process.argv.includes('--smoke-test')
let mainWindow = null
let backendProcess = null
let backendExited = false
let backendExitCode = null
let quitting = false
let ready = false
let localOrigin = ''

function backendExecutable() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'backend', 'wanshiwu-backend.exe')
    : path.join(__dirname, 'dist', 'backend', 'wanshiwu-backend', 'wanshiwu-backend.exe')
}

function prepareLog() {
  const directory = process.env.WANSHIWU_LOG_DIR || path.join(app.getPath('userData'), 'logs')
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
    env: { ...process.env, WANSHIWU_PORT: String(port) },
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
    if (!quitting && ready) {
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
    },
  })
  mainWindow.loadFile(path.join(__dirname, 'loading.html'))
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
  return logFile
}

async function startWithRecovery() {
  try {
    await openApplication()
  } catch (error) {
    stopBackend()
    const detail = error instanceof Error ? error.message : String(error)
    if (SMOKE_TEST) {
      console.error(`WANSHIWU_DESKTOP_SMOKE_FAILED ${detail}`)
      app.exit(1)
      return
    }
    const logDirectory = process.env.WANSHIWU_LOG_DIR || path.join(app.getPath('userData'), 'logs')
    const { response } = await dialog.showMessageBox({
      type: 'error',
      title: '万事屋暂时未能启动',
      message: '万事屋暂时未能启动',
      detail: `${detail}\n\n可以点击“重试”。若仍失败，请把日志发给软件提供者：\n${path.join(logDirectory, 'backend.log')}`,
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
