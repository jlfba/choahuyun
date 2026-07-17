<template>
  <div class="app">
    <!-- 顶部导航 -->
    <header>
      <div class="header-left">
        <div class="logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>
          </svg>
          <h1>通话记录</h1>
        </div>
      </div>
      <div class="header-right">
        <span class="badge">{{ filteredRecords.length }} 条记录</span>
      </div>
    </header>

    <!-- 筛选栏 -->
    <div class="filters">
      <div class="filter-group">
        <label>日期</label>
        <select v-model="selectedDate" @change="currentPage = 1; loadRecords()">
          <option value="">全部日期</option>
          <option v-for="d in dates" :key="d.date" :value="d.date">
            {{ d.date }} ({{ d.count }}条)
          </option>
        </select>
      </div>
      <div class="filter-group search-group">
        <label>搜索</label>
        <div class="search-input">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input v-model="search" @input="currentPage = 1" placeholder="主叫、被叫、客户、转写文字..." />
        </div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-wrapper"
         @mousemove="onTableMove"
         @mouseleave="onCellLeave">
      <table>
        <thead>
          <tr>
            <th v-for="col in columns" :key="col.key" @click="sort(col.key)"
                :class="{ active: sortKey === col.key }" :style="{ width: col.width || 'auto' }">
              <span>{{ col.label }}</span>
              <svg v-if="sortKey === col.key" width="12" height="12" viewBox="0 0 24 24"
                   :style="{ transform: sortDir === 'desc' ? 'rotate(180deg)' : '' }">
                <path d="M12 4l-8 8h16z" fill="currentColor"/>
              </svg>
            </th>
            <th style="width:220px">录音</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in paginatedRecords" :key="row.id"
              :class="{ 'row-playing': playingId === row.id }">
            <td v-for="(col, ci) in columns" :key="col.key"
                :data-tip="cleanText(row[col.key])">
              <span v-if="col.key === 'status'" :class="'status-' + row.status">{{ row.status }}</span>
              <span v-else-if="col.key === 'caller' || col.key === 'callee'" class="phone">{{ row[col.key] }}</span>
              <span v-else>{{ truncate(row[col.key], col.truncate || 30) }}</span>
            </td>
            <td class="audio-cell">
              <div v-if="row.audio_url" class="audio-player">
                <audio :src="row.audio_url" controls preload="metadata"
                       @play="playingId = row.id" @pause="playingId = null"
                       @ended="playingId = null" />
              </div>
              <span v-else class="no-audio">无录音</span>
            </td>
          </tr>
          <tr v-if="filteredRecords.length === 0">
            <td :colspan="columns.length + 1" class="empty">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5">
                <path d="M9 18l6-6-6-6"/>
              </svg>
              <p>暂无数据</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="totalPages > 1">
      <button :disabled="currentPage <= 1" @click="currentPage--">上一页</button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
    </div>

    <!-- 悬浮提示 (用ref直接操作DOM) -->
    <div ref="tipEl" class="tooltip-box" style="display:none"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const API = ''

const columns = [
  { key: 'id', label: '#', width: '50px' },
  { key: 'caller', label: '主叫', width: '130px' },
  { key: 'callee', label: '被叫', width: '130px' },
  { key: 'company', label: '公司信息', width: '140px', truncate: 15 },
  { key: 'status', label: '状态', width: '80px' },
  { key: 'connect_time', label: '接通时间', width: '160px' },
  { key: 'hangup_time', label: '挂断时间', width: '160px' },
  { key: 'mark', label: '标记', width: '80px', truncate: 10 },
  { key: 'customer_name', label: '客户', width: '80px', truncate: 10 },
  { key: 'customer_company', label: '客户公司', width: '120px', truncate: 15 },
  { key: 'transcription', label: '转写文字', truncate: 50 },
]

const dates = ref([])
const selectedDate = ref('')
const records = ref([])
const search = ref('')
const sortKey = ref('')
const sortDir = ref('asc')
const currentPage = ref(1)
const pageSize = 50

const filteredRecords = computed(() => {
  let data = records.value
  if (search.value) {
    const q = search.value.toLowerCase()
    data = data.filter(r =>
      r.caller.includes(q) ||
      r.callee.includes(q) ||
      r.transcription.toLowerCase().includes(q) ||
      r.customer_name.includes(q) ||
      r.customer_company.includes(q)
    )
  }
  if (sortKey.value) {
    data = [...data].sort((a, b) => {
      const va = a[sortKey.value] || ''
      const vb = b[sortKey.value] || ''
      return sortDir.value === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })
  }
  return data
})
const totalPages = computed(() => Math.ceil(filteredRecords.value.length / pageSize))
const paginatedRecords = computed(() => {
  const s = (currentPage.value - 1) * pageSize
  return filteredRecords.value.slice(s, s + pageSize)
})

const playingId = ref(null)
const tipEl = ref(null)
let lastTd = null
let rafId = null
let tipW = 0, tipH = 0

function onTableMove(e) {
  if (!tipEl.value) return

  const td = e.target.closest('td')
  if (!td) { onCellLeave(); return }

  // 进入新 td 时更新内容
  if (td !== lastTd) {
    lastTd = td
    const text = td.getAttribute('data-tip')
    if (!text) { onCellLeave(); return }
    tipEl.value.textContent = text
    tipEl.value.style.visibility = 'hidden'
    tipEl.value.style.display = 'block'
    tipW = tipEl.value.offsetWidth
    tipH = tipEl.value.offsetHeight
    tipEl.value.style.visibility = ''
  }

  // 位置用 rAF 合并，避免每帧都写 DOM
  if (rafId) return
  const mx = e.clientX, my = e.clientY
  rafId = requestAnimationFrame(() => {
    rafId = null
    if (!tipEl.value || tipEl.value.style.display === 'none') return
    let x = mx + 14
    let y = my - 14
    if (x + tipW > window.innerWidth - 8) x = mx - tipW - 14
    if (y + tipH > window.innerHeight - 8) y = my - tipH - 14
    if (y < 8) y = 8
    tipEl.value.style.transform = `translate(${x}px, ${y}px)`
  })
}
function onCellLeave() {
  if (tipEl.value) tipEl.value.style.display = 'none'
  lastTd = null
}

function truncate(str, len) {
  if (!str) return ''
  const s = String(str).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')
  return s.length > len ? s.slice(0, len) + '...' : s
}

function cleanText(str) {
  if (!str) return ''
  return String(str).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')
}

function sort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

async function loadDates() {
  const res = await fetch(`${API}/api/dates`)
  dates.value = await res.json()
  if (dates.value.length > 0) {
    selectedDate.value = dates.value[dates.value.length - 1].date
    await loadRecords()
  }
}

async function loadRecords() {
  const url = selectedDate.value
    ? `${API}/api/records?date=${selectedDate.value}`
    : `${API}/api/records`
  const res = await fetch(url)
  records.value = await res.json()
}

onMounted(loadDates)
</script>

<style>
:root {
  --bg: #f0f2f5;
  --card: #ffffff;
  --primary: #4f6ef7;
  --primary-light: #eef1fe;
  --text: #1a1a2e;
  --text2: #6b7280;
  --border: #e5e7eb;
  --green: #10b981;
  --red: #ef4444;
  --orange: #f59e0b;
  --radius: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  height: 100%;
  overflow: hidden;
}

.app {
  padding: 20px 24px;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Header */
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary);
}
.logo h1 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}
.badge {
  background: var(--primary-light);
  color: var(--primary);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

/* Filters */
.filters {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
  padding: 14px 20px;
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  flex-shrink: 0;
}
.filter-group { display: flex; flex-direction: column; gap: 6px; }
.filter-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.filter-group select,
.filter-group input {
  padding: 9px 14px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text);
  background: #fff;
  transition: border-color 0.2s;
  outline: none;
}
.filter-group select:focus,
.filter-group input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 110, 247, 0.1);
}
.filter-group select { min-width: 200px; }
.search-group { flex: 1; }
.search-input {
  position: relative;
  display: flex;
  align-items: center;
}
.search-input svg {
  position: absolute;
  left: 12px;
  color: var(--text2);
  pointer-events: none;
}
.search-input input {
  padding-left: 36px;
  width: 100%;
}

/* Table */
.table-wrapper {
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: auto;
  flex: 1;
  min-height: 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
thead {
  position: sticky;
  top: 0;
  z-index: 2;
}
th {
  background: #f9fafb;
  padding: 12px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1.5px solid var(--border);
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}
th span { vertical-align: middle; }
th svg { vertical-align: middle; margin-left: 2px; }
th.active { color: var(--primary); background: var(--primary-light); }

td {
  padding: 10px;
  border-bottom: 1px solid #f3f4f6;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  vertical-align: middle;
}

tr:hover td { background: #f9fafb; }
tr.row-playing td {
  background: var(--primary-light);
  border-color: rgba(79,110,247,0.15);
}

.phone {
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  font-size: 12.5px;
  color: var(--primary);
  font-weight: 500;
}

.status-接通 { color: var(--green); font-weight: 600; }
.status-未接通 { color: var(--red); font-weight: 500; }
.status-拨号中 { color: var(--orange); font-weight: 500; }

.audio-cell { white-space: nowrap; padding: 6px 8px; }
.audio-player audio {
  width: 200px;
  height: 32px;
  border-radius: 6px;
}
.no-audio {
  color: #d1d5db;
  font-size: 12px;
  font-style: italic;
}

/* 悬浮提示 */
.tooltip-box {
  position: fixed;
  left: 0; top: 0;
  z-index: 99999;
  background: #1a1a2e;
  color: #fff;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-width: 500px;
  min-width: 120px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  pointer-events: none;
  will-change: transform;
}

.empty {
  text-align: center;
  padding: 60px 20px !important;
  color: var(--text2);
}
.empty p { margin-top: 8px; font-size: 15px; }

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  flex-shrink: 0;
}
.pagination button {
  padding: 8px 20px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  background: #fff;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.pagination button:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--text2);
  font-weight: 600;
}
</style>
