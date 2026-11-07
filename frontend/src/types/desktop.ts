export interface DesktopDataLocation {
  dataDir: string
  installDir: string
  fallbackDir: string
  defaultDir: string
  source: 'env' | 'custom' | 'install' | 'fallback' | 'pointer-unusable'
  reason: string
  pointerFile: string
  logFile: string
  legacyDir: string
  legacyHasData: boolean
  migrated: boolean
  migrationError: string | null
  usingLegacy: boolean
  systemDrive: string
  platform: string
  version: string
}

export interface DesktopActionResult {
  ok: boolean
  canceled?: boolean
  message?: string
  restarting?: boolean
  dataDir?: string
}

export interface DesktopBridge {
  isDesktop: boolean
  getDataLocation(): Promise<DesktopDataLocation>
  chooseDataLocation(): Promise<DesktopActionResult>
  openDataFolder(): Promise<DesktopActionResult>
  openLegacyFolder(): Promise<DesktopActionResult>
}

declare global {
  interface Window {
    wanshiwuDesktop?: DesktopBridge
  }
}
