// 待辦清單檔的格式: 每筆一行 `- [ ] 內容 (YYYY-MM-DD)`; 其他行(標題、手寫備註)原樣保留
const ITEM = /^- \[[ xX]\] (.+)$/
const HEADER = '# TODO\n\n'

export function todayText(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function parseTodos(md: string): string[] {
  return md
    .split(/\r?\n/)
    .map(line => line.match(ITEM)?.[1]?.trim())
    .filter((item): item is string => !!item)
}

// 加在清單最後; 檔案還不存在(空字串)時補上標題
export function addTodo(md: string, text: string, date: string): string {
  const line = `- [ ] ${text.replace(/\s*\r?\n\s*/g, ' ')} (${date})`
  if (!md.trim()) return `${HEADER}${line}\n`
  return `${md.replace(/\s*$/, '')}\n${line}\n`
}

// 只刪第一筆內容相符的; 找不到就原樣不動(可能已在別處刪掉)
export function removeTodo(md: string, item: string): string {
  const lines = md.split(/\r?\n/)
  const at = lines.findIndex(line => line.match(ITEM)?.[1]?.trim() === item)
  if (at < 0) return md
  lines.splice(at, 1)
  return lines.join('\n')
}
