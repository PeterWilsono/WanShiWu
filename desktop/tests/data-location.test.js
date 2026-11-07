'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')

const {
  ensureDataDirectory,
  hasDatabase,
  moveDataTo,
  readPointer,
  resolveDataLocation,
  writePointer,
} = require('../data-location')

const BASE = path.join(__dirname, '.tmp-data-location', String(process.pid))

function freshRoot(name) {
  const root = path.join(BASE, name)
  fs.rmSync(root, { recursive: true, force: true })
  fs.mkdirSync(root, { recursive: true })
  return root
}

function writeDatabase(directory, content = 'sqlite-bytes') {
  fs.mkdirSync(directory, { recursive: true })
  fs.writeFileSync(path.join(directory, 'wanshiwu.db'), content)
}

test.before(() => fs.rmSync(BASE, { recursive: true, force: true }))
test.after(() => fs.rmSync(BASE, { recursive: true, force: true }))

test('默认把数据放进安装目录下的 data', () => {
  const appDir = freshRoot('default-install')
  const localRoot = freshRoot('default-local')
  const result = resolveDataLocation({ appDir, env: {}, localRoot })
  assert.equal(result.source, 'install')
  assert.equal(result.dataDir, path.join(appDir, 'data'))
})

test('安装目录位于系统临时目录时改用本机默认目录', () => {
  const appDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wanshiwu-temp-'))
  const localRoot = freshRoot('temp-local')
  const result = resolveDataLocation({ appDir, env: {}, localRoot })
  assert.equal(result.source, 'fallback')
  assert.equal(result.dataDir, path.join(localRoot, 'data'))
  fs.rmSync(appDir, { recursive: true, force: true })
})

test('用户设置的位置优先于安装目录', () => {
  const appDir = freshRoot('pointer-install')
  const localRoot = freshRoot('pointer-local')
  const custom = path.join(freshRoot('pointer-custom'), '我的数据')
  fs.mkdirSync(custom, { recursive: true })
  writePointer(path.join(localRoot, 'data-location.json'), custom)

  const result = resolveDataLocation({ appDir, env: {}, localRoot })
  assert.equal(result.source, 'custom')
  assert.equal(result.dataDir, custom)
  assert.equal(readPointer(path.join(localRoot, 'data-location.json')).dataDir, custom)
})

test('指针指向的位置不可用时回退到安装目录', () => {
  const appDir = freshRoot('broken-pointer-install')
  const localRoot = freshRoot('broken-pointer-local')
  const blocked = path.join(freshRoot('broken-pointer-target'), 'a-file')
  fs.writeFileSync(blocked, 'not a directory')
  writePointer(path.join(localRoot, 'data-location.json'), blocked)

  const result = resolveDataLocation({ appDir, env: {}, localRoot })
  assert.equal(result.source, 'pointer-unusable')
  assert.equal(result.dataDir, path.join(appDir, 'data'))
})

test('环境变量用于开发调试时优先级最高', () => {
  const appDir = freshRoot('env-install')
  const localRoot = freshRoot('env-local')
  const custom = freshRoot('env-custom')
  const result = resolveDataLocation({
    appDir,
    env: { WANSHIWU_DATA_DIR: custom },
    localRoot,
  })
  assert.equal(result.source, 'env')
  assert.equal(result.dataDir, custom)
})

test('新位置为空时把旧位置数据库复制过来', () => {
  const legacy = freshRoot('migrate-legacy')
  const target = path.join(freshRoot('migrate-target'), 'data')
  writeDatabase(legacy, 'legacy-content')
  fs.writeFileSync(path.join(legacy, 'jwt-secret.txt'), 'secret')

  const ensured = ensureDataDirectory(target, { legacyDir: legacy })
  assert.equal(ensured.migrated, true)
  assert.equal(ensured.dataDir, target)
  assert.equal(fs.readFileSync(path.join(target, 'wanshiwu.db'), 'utf8'), 'legacy-content')
  assert.equal(fs.readFileSync(path.join(target, 'jwt-secret.txt'), 'utf8'), 'secret')
  // 迁移后旧数据仍在，作为兜底备份。
  assert.equal(hasDatabase(legacy), true)
})

test('新位置已有数据库时不覆盖', () => {
  const legacy = freshRoot('keep-legacy')
  const target = freshRoot('keep-target')
  writeDatabase(legacy, 'old')
  writeDatabase(target, 'current')

  const ensured = ensureDataDirectory(target, { legacyDir: legacy })
  assert.equal(ensured.migrated, false)
  assert.equal(fs.readFileSync(path.join(target, 'wanshiwu.db'), 'utf8'), 'current')
})

test('旧位置没有数据时不会报错', () => {
  const legacy = freshRoot('empty-legacy')
  const target = path.join(freshRoot('empty-target'), 'data')
  const ensured = ensureDataDirectory(target, { legacyDir: legacy })
  assert.equal(ensured.migrated, false)
  assert.equal(ensured.error, null)
  assert.equal(fs.existsSync(target), true)
})

test('主动迁移到新文件夹并校验大小', () => {
  const source = freshRoot('move-source')
  const target = path.join(freshRoot('move-target'), '新位置')
  writeDatabase(source, 'payload-123')

  const result = moveDataTo(target, { sourceDir: source })
  assert.equal(result.ok, true)
  assert.equal(fs.readFileSync(path.join(target, 'wanshiwu.db'), 'utf8'), 'payload-123')
  assert.equal(hasDatabase(source), true)
})

test('目标已有数据或位置不合法时拒绝覆盖', () => {
  const source = freshRoot('reject-source')
  const target = freshRoot('reject-target')
  writeDatabase(source, 'payload')
  writeDatabase(target, 'other')

  assert.equal(moveDataTo(target, { sourceDir: source }).code, 'target-has-data')
  assert.equal(moveDataTo(source, { sourceDir: source }).ok, false)

  const temporary = path.join(os.tmpdir(), 'wanshiwu-reject-temp')
  fs.mkdirSync(temporary, { recursive: true })
  assert.equal(moveDataTo(temporary, { sourceDir: source }).ok, false)
  fs.rmSync(temporary, { recursive: true, force: true })
  assert.equal(fs.readFileSync(path.join(target, 'wanshiwu.db'), 'utf8'), 'other')
})
