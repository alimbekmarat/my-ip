export type IpInfo = {
  ip: string | null
  geo: string
  checkedAt: number
  error: string | null
  isBusy: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'my-ip': { info: IpInfo; prevIp: string | null }
  }
}
