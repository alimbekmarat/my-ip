import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { IpInfo } from '../types'

const EMPTY: IpInfo = { ip: null, geo: '', checkedAt: 0, error: null, isBusy: false }
const info = atom({ plugin: 'my-ip', key: 'info' } as const, EMPTY, { shape: 'ip-1' })
const prevIp = atom({ plugin: 'my-ip', key: 'prevIp' } as const, null)

const INTERVAL_MS = 60_000

// Несколько сервисов по очереди: если один не ответил, берём следующий
const PROVIDERS: { url: string; parse: (d: any) => { ip?: string; geo: string } }[] = [
  { url: 'https://ipwho.is/', parse: d => ({ ip: d.ip, geo: [d.city, d.country].filter(Boolean).join(', ') }) },
  { url: 'https://ipapi.co/json/', parse: d => ({ ip: d.ip, geo: [d.city, d.country_name].filter(Boolean).join(', ') }) },
  { url: 'https://api.ipify.org?format=json', parse: d => ({ ip: d.ip, geo: '' }) },
]

const hhmm = (ms: number) => {
  const d = new Date(ms)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

let isRunning = false

async function check($: any) {
  if (isRunning) return
  isRunning = true
  await update($, info, v => ({ ...v, isBusy: true }))
  const now = await $.clock.now()
  try {
    for (const p of PROVIDERS) {
      try {
        const r = await $.http.fetch(p.url)
        if (!r.ok) continue
        const res = p.parse(JSON.parse(r.text))
        if (!res.ip) continue
        const before = await read($, prevIp)
        if (before && before !== res.ip) $.ui.toast(`IP сменился: ${before} → ${res.ip}`)
        await update($, prevIp, () => res.ip!)
        await update($, info, () => ({ ip: res.ip!, geo: res.geo, checkedAt: now, error: null, isBusy: false }))
        return
      } catch {
        // следующий сервис
      }
    }
    await update($, info, v => ({ ...v, checkedAt: now, error: 'нет ответа от сервисов', isBusy: false }))
  } finally {
    isRunning = false
  }
}


export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'ip', description: 'Проверить внешний IP прямо сейчас' })
    void check($)
    $.clock.every(INTERVAL_MS, () => check($))
    return next(e)
  })

  on('command.run', { command: 'ip' }, async $ => {
    await check($)
    const v = await read($, info)
    return { text: v.ip ? `IP: ${v.ip}${v.geo ? ' · ' + v.geo : ''}` : `Не удалось узнать IP: ${v.error ?? 'ошибка'}` }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const v = await read($, info)
    const { Box, Button, Text } = $.ui.resolve(e)

    const label = v.isBusy && !v.ip
      ? 'IP: проверяю…'
      : v.ip
        ? `IP: ${v.ip}${v.geo ? ' · ' + v.geo : ''}`
        : `IP: ${v.error ?? '—'}`
    const when = v.checkedAt ? ` (проверено ${hhmm(v.checkedAt)})` : ''

    return (
      <Box>
        <Text color={v.error && !v.ip ? 'red' : undefined}>{label}</Text>
        <Text dimColor>{when} </Text>
        <Button key="refresh" label={v.isBusy ? 'Проверяю…' : 'Обновить'} onPress={() => check($)} />
      </Box>
    )
  })
}
