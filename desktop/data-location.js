'use strict'

/**
 * 数据目录解析与迁移。
 *
 * 目标：桌面版业务数据默认跟着软件走（安装目录下的 data），不再强制放在 C 盘；
 * 用户也可以在软件内改到任意磁盘。这里刻意不依赖 Electron，方便独立测试。
 */

const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

const DB_FILE = 'wanshiwu.db'
const POINTER_FILE = 'data-location.json'
/** 需要随数据一起搬迁的文件；顺序固定，数据库文件在最后校验。 */
const DATA_FILES = ['jwt-secret.txt', DB_FILE, `${DB_FILE}-wal`, `${DB_FILE}-shm`]

function systemLocalRoot(env = process.env, platform = process.platform) {
  if (platform === 'win32') {
    const local = env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local')
    return path.join(local, 'WanShiWu')
  }
  return path.join(os.homedir(), '.wanshiwu')
}

function isWritableDirectory(directory) {
  try {
    fs.mkdirSync(directory, { recursive: true })
  } catch {
    return false
  }
  const probe = path.join(directory, `.write-check-${process.pid}-${Date.now()}`)
  try {
    fs.writeFileSync(probe, 'ok')
  } catch {
    return false
  }
  try {
    fs.unlinkSync(probe)
  } catch {
    // 清理探测文件失败不影响“可写”的判断。
  }
  return true
}

function isTemporaryPath(target) {
  const normalized = path.resolve(target).toLowerCase()
  const temporary = path.resolve(os.tmpdir()).toLowerCase()
  return normalized === temporary || normalized.startsWith(`${temporary}${path.sep}`)
}

function readPointer(pointerFile) {
  try {
    const raw = fs.readFileSync(pointerFile, 'utf8')
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed.dataDir !== 'string' || !parsed.dataDir.trim()) return null
    return { dataDir: path.resolve(parsed.dataDir.trim()) }
  } catch {
    return null
  }
}

function writePointer(pointerFile, dataDir) {
  fs.mkdirSync(path.dirname(pointerFile), { recursive: true })
  const payload = { dataDir: path.resolve(dataDir), updatedAt: new Date().toISOString() }
  const temporary = `${pointerFile}.tmp`
  fs.writeFileSync(temporary, JSON.stringify(payload, null, 2), 'utf8')
  fs.renameSync(temporary, pointerFile)
  return payload
}

function hasDatabase(directory) {
  try {
    return fs.statSync(path.join(directory, DB_FILE)).isFile()
  } catch {
    return false
  }
}

/**
 * 决定本次启动使用的数据目录。
 * 顺序：环境变量（开发/测试）→ 用户自定义指针 → 安装目录 data → 系统本地目录。
 */
function resolveDataLocation(options) {
  const appDir = path.resolve(options.appDir)
  const env = options.env || process.env
  const localRoot = options.localRoot || systemLocalRoot(env)
  const installDir = path.join(appDir, 'data')
  const fallbackDir = path.join(localRoot, 'data')
  const pointerFile = path.join(localRoot, POINTER_FILE)

  const configured = (env.WANSHIWU_DATA_DIR || '').trim()
  if (configured) {
    return {
      dataDir: path.resolve(configured),
      installDir,
      fallbackDir,
      pointerFile,
      source: 'env',
      reason: '由 WANSHIWU_DATA_DIR 指定',
    }
  }

  const pointer = readPointer(pointerFile)
  if (pointer) {
    if (isWritableDirectory(pointer.dataDir)) {
      return {
        dataDir: pointer.dataDir,
        installDir,
        fallbackDir,
        pointerFile,
        source: 'custom',
        reason: '使用软件内设置的保存位置',
      }
    }
    return {
      dataDir: isWritableDirectory(installDir) && !isTemporaryPath(installDir) ? installDir : fallbackDir,
      installDir,
      fallbackDir,
      pointerFile,
      source: 'pointer-unusable',
      reason: '之前设置的位置当前不可用，已临时改用其他目录',
    }
  }

  if (isWritableDirectory(installDir) && !isTemporaryPath(installDir)) {
    return {
      dataDir: installDir,
      installDir,
      fallbackDir,
      pointerFile,
      source: 'install',
      reason: '默认保存在软件目录下的 data 文件夹',
    }
  }

  return {
    dataDir: fallbackDir,
    installDir,
    fallbackDir,
    pointerFile,
    source: 'fallback',
    reason: '软件目录不可写或位于临时目录，改用系统本地目录',
  }
}

function copyDataFiles(from, to, files = DATA_FILES) {
  const copied = []
  for (const name of files) {
    const source = path.join(from, name)
    let stat
    try {
      stat = fs.statSync(source)
    } catch {
      continue
    }
    if (!stat.isFile()) continue
    const target = path.join(to, name)
    fs.copyFileSync(source, target)
    const copiedStat = fs.statSync(target)
    if (copiedStat.size !== stat.size) {
      throw new Error(`复制 ${name} 后大小不一致`)
    }
    copied.push(name)
  }
  return copied
}

function removeDataFiles(directory) {
  for (const name of DATA_FILES) {
    try {
      fs.unlinkSync(path.join(directory, name))
    } catch {
      // 文件可能本来就不存在，忽略。
    }
  }
}

/**
 * 确保数据目录可用，并在新目录为空时把旧目录数据搬过来。
 * 迁移失败时回退到旧目录，避免软件用空数据库启动、看起来像数据丢失。
 */
function ensureDataDirectory(dataDir, options = {}) {
  const legacyDir = options.legacyDir ? path.resolve(options.legacyDir) : null
  const skipLegacy = options.skipLegacy === true

  if (!isWritableDirectory(dataDir)) {
    if (legacyDir && hasDatabase(legacyDir)) {
      return { dataDir: legacyDir, migrated: false, fallback: true, error: '数据目录不可写' }
    }
    throw new Error(`数据目录不可写：${dataDir}`)
  }

  if (skipLegacy || !legacyDir || legacyDir === dataDir || hasDatabase(dataDir) || !hasDatabase(legacyDir)) {
    return { dataDir, migrated: false, fallback: false, error: null }
  }

  try {
    const copied = copyDataFiles(legacyDir, dataDir)
    if (!copied.includes(DB_FILE)) throw new Error('未能复制数据库文件')
    const sourceSize = fs.statSync(path.join(legacyDir, DB_FILE)).size
    const targetSize = fs.statSync(path.join(dataDir, DB_FILE)).size
    if (sourceSize !== targetSize) throw new Error('数据库大小校验失败')
    return { dataDir, migrated: true, fallback: false, error: null, files: copied }
  } catch (error) {
    removeDataFiles(dataDir)
    return {
      dataDir: legacyDir,
      migrated: false,
      fallback: true,
      error: `迁移旧数据失败：${error.message}`,
    }
  }
}

/**
 * 把当前数据搬迁到用户选择的目录。调用方必须先停掉后端进程。
 * 目标目录若已有本软件数据，则默认拒绝覆盖。
 */
function moveDataTo(targetDir, options = {}) {
  const sourceDir = path.resolve(options.sourceDir)
  const target = path.resolve(targetDir)
  const overwrite = options.overwrite === true

  if (target === sourceDir) return { ok: false, message: '新位置与当前位置相同' }
  if (isTemporaryPath(target)) return { ok: false, message: '不能把数据放在系统临时目录' }
  if (!isWritableDirectory(target)) return { ok: false, message: '这个文件夹无法写入，请换一个位置' }
  if (!hasDatabase(sourceDir)) return { ok: false, message: '当前还没有可迁移的数据' }
  if (hasDatabase(target) && !overwrite) {
    return { ok: false, code: 'target-has-data', message: '目标文件夹已有万事屋数据' }
  }

  try {
    const copied = copyDataFiles(sourceDir, target)
    if (!copied.includes(DB_FILE)) throw new Error('未能复制数据库文件')
    const sourceSize = fs.statSync(path.join(sourceDir, DB_FILE)).size
    const targetSize = fs.statSync(path.join(target, DB_FILE)).size
    if (sourceSize !== targetSize) throw new Error('数据库大小校验失败')
    return { ok: true, dataDir: target, files: copied, sourceDir }
  } catch (error) {
    removeDataFiles(target)
    return { ok: false, message: `迁移失败：${error.message}` }
  }
}

module.exports = {
  DB_FILE,
  DATA_FILES,
  POINTER_FILE,
  ensureDataDirectory,
  hasDatabase,
  isTemporaryPath,
  isWritableDirectory,
  moveDataTo,
  readPointer,
  resolveDataLocation,
  systemLocalRoot,
  writePointer,
}
