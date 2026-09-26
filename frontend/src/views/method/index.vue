<template>
  <section class="page" data-module="method">
    <header class="page-head">
      <div>
        <h2>检测方法管理</h2>
        <p class="page-desc">维护检测方法，围绕方法编号、标准编号与版本号组合检索；同一方法编号的历史版本可展开定位。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记检测方法</button>
        <button class="btn" type="button" @click="exportRows">导出检测方法清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>方法编号</span>
        <input v-model="draftFilters.methodNo" placeholder="如 METH-0002" />
      </label>
      <label class="filter-item">
        <span>标准编号</span>
        <input v-model="draftFilters.standardNo" placeholder="如 HJ 828" />
      </label>
      <label class="filter-item">
        <span>版本号</span>
        <input v-model="draftFilters.version" placeholder="如 2017" />
      </label>
      <label class="filter-item">
        <span>方法状态</span>
        <select v-model="draftFilters.status">
          <option value="">全部状态</option>
          <option value="active">仅现行有效 / 备选</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn primary" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table method-table">
      <thead>
        <tr>
          <th class="col-toggle"></th>
          <th>方法编号</th>
          <th>方法名称</th>
          <th>标准编号</th>
          <th>版本号</th>
          <th>适用范围</th>
          <th>检出限</th>
          <th>精密度</th>
          <th>方法状态</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody v-if="rows.length">
        <template v-for="group in rows" :key="group['方法编号']">
          <tr class="group-head-row" :class="{ 'is-expanded': isExpanded(group['方法编号']) }">
            <td class="col-toggle">
              <button
                class="toggle-btn"
                type="button"
                :aria-expanded="isExpanded(group['方法编号'])"
                @click="toggleGroup(group['方法编号'])"
              >
                {{ isExpanded(group['方法编号']) ? '▾' : '▸' }}
              </button>
            </td>
            <td>{{ group['方法编号'] }}</td>
            <td>{{ group.head['方法名称'] }}</td>
            <td>{{ group.head['标准编号'] }}</td>
            <td>{{ group.head['版本号'] }}</td>
            <td>{{ group.head['适用范围'] }}</td>
            <td>{{ group.head['检出限'] }}</td>
            <td>{{ group.head['精密度'] }}</td>
            <td>
              <span class="status-badge" :class="badgeClass(group.head['方法状态'])">{{ group.head['方法状态'] }}</span>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(group.head.id)">查看详情</button>
              <button
                v-for="action in actionsFor(group.head['方法状态'])"
                :key="action"
                class="link"
                type="button"
                @click="runAction(action, group.head)"
              >
                {{ action }}
              </button>
            </td>
          </tr>
          <template v-if="isExpanded(group['方法编号'])">
            <tr
              v-for="version in group.versions"
              :key="String(version.id)"
              class="version-row"
              :class="{ 'version-hit': version.matched, 'version-locate': isLocate(version.id) }"
              :ref="registerVersionRow"
              :data-version-id="version.id"
            >
              <td class="col-toggle"></td>
              <td class="version-cell">{{ group['方法编号'] }}</td>
              <td class="version-cell">{{ version['方法名称'] }}</td>
              <td class="version-cell">{{ version['标准编号'] }}</td>
              <td class="version-cell">
                <span class="version-no">{{ version['版本号'] }}</span>
                <span v-if="version.id === group.head.id" class="version-tag">主版本</span>
                <span v-if="version.matched" class="version-hit-tag">命中</span>
              </td>
              <td class="version-cell">{{ version['适用范围'] }}</td>
              <td class="version-cell">{{ version['检出限'] }}</td>
              <td class="version-cell">{{ version['精密度'] }}</td>
              <td class="version-cell">
                <span class="status-badge" :class="badgeClass(version['方法状态'])">{{ version['方法状态'] }}</span>
              </td>
              <td class="row-actions version-cell">
                <button class="link" type="button" @click="openDetail(version.id)">查看详情</button>
                <button
                  v-for="action in actionsFor(version['方法状态'])"
                  :key="action"
                  class="link"
                  type="button"
                  @click="runAction(action, version)"
                >
                  {{ action }}
                </button>
              </td>
            </tr>
          </template>
        </template>
      </tbody>
      <tbody v-else>
        <tr>
          <td colspan="10" class="empty-state">
            <template v-if="loading">正在加载检测方法…</template>
            <template v-else>
              <p class="empty-title">未找到符合条件的检测方法</p>
              <p class="empty-desc">
                当前条件：方法编号「{{ draftFilters.methodNo || '不限' }}」、标准编号「{{ draftFilters.standardNo || '不限' }}」、版本号「{{ draftFilters.version || '不限' }}」、状态「{{ statusLabel(draftFilters.status) }}」
              </p>
              <p v-if="page > totalPages" class="empty-desc">
                第 {{ page }} 页已超出可用范围（共 {{ totalPages }} 页），可返回上一页继续查看。
              </p>
              <p class="empty-desc">可调整检索条件后重新查询，或重置为全部方法。</p>
              <button v-if="page > totalPages" class="btn" type="button" @click="goPage(totalPages)">回到最后一页</button>
              <button class="btn" type="button" @click="resetFilters">重置条件</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot method-foot">
      <span>共 {{ total }} 个方法编号{{ total ? `（第 ${page} / ${totalPages} 页）` : '' }}</span>
      <div class="pager">
        <button class="btn" type="button" :disabled="page <= 1" @click="goPage(1)">首页</button>
        <button class="btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <button
          v-for="item in pageItems"
          :key="item"
          class="btn"
          :class="{ primary: item === page }"
          type="button"
          @click="goPage(item)"
        >
          {{ item }}
        </button>
        <button class="btn" type="button" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
        <label class="size-item">
          每页
          <select v-model.number="size" @change="changeSize">
            <option :value="5">5</option>
            <option :value="10">10</option>
            <option :value="20">20</option>
          </select>
          个
        </label>
      </div>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, type ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type MethodStatus = '现行有效' | '修订中' | '已废止' | '备选'

type VersionRow = {
  id: number
  方法编号?: string
  方法名称: string
  标准编号: string
  适用范围: string
  检出限: string
  精密度: string
  版本号: string
  方法状态: MethodStatus
  matched: boolean
}

type MethodGroup = {
  方法编号: string
  head: VersionRow
  versions: VersionRow[]
  matchedCount: number
}

type Filters = {
  methodNo: string
  standardNo: string
  version: string
  status: string
}

const ENDPOINT = '/api/method'
const statuses: MethodStatus[] = ['现行有效', '修订中', '已废止', '备选']

const EMPTY_FILTERS: Filters = { methodNo: '', standardNo: '', version: '', status: '' }

const route = useRoute()
const router = useRouter()

const rows = ref<MethodGroup[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const draftFilters = ref<Filters>({ ...EMPTY_FILTERS })
const expanded = ref<Set<string>>(new Set())
const filterSignature = ref('')
const versionRowEls = new Map<number, HTMLElement>()
const statValues = ref<Record<string, number>>({ 现行有效: 0, 修订中: 0, 已废止: 0, 备选: 0 })

const stats = computed(() => [
  { label: '现行有效', value: statValues.value['现行有效'] ?? 0 },
  { label: '备选方法', value: statValues.value['备选'] ?? 0 },
  { label: '修订中方法', value: statValues.value['修订中'] ?? 0 },
  { label: '废止方法', value: statValues.value['已废止'] ?? 0 },
])

const page = computed(() => {
  const value = Number(route.query.page ?? 1)
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1
})
const size = ref(Number(route.query.size ?? 10) === 5 ? 5 : Number(route.query.size) === 20 ? 20 : 10)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

const pageItems = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, Math.min(page.value - 2, totalPages.value - 4))
  for (let item = start; item <= Math.min(totalPages.value, start + 4); item += 1) {
    pages.push(item)
  }
  return pages
})

function badgeClass(status: string) {
  return {
    'status-active': status === '现行有效',
    'status-backup': status === '备选',
    'status-revising': status === '修订中',
    'status-revoked': status === '已废止',
  }
}

function statusLabel(status: string) {
  if (!status) {
    return '全部状态'
  }
  return status === 'active' ? '仅现行有效 / 备选' : status
}

function actionsFor(status: string): string[] {
  if (status === '现行有效') {
    return ['废止方法', '修订方法']
  }
  if (status === '备选') {
    return ['启用方法', '废止方法']
  }
  if (status === '修订中') {
    return ['启用方法', '废止方法']
  }
  return ['启用方法']
}

function readFiltersFromRoute(): Filters {
  const pick = (key: string) => (typeof route.query[key] === 'string' ? String(route.query[key]) : '')
  return {
    methodNo: pick('methodNo'),
    standardNo: pick('standardNo'),
    version: pick('version'),
    status: pick('status'),
  }
}

function buildQuery(overrides: Record<string, string | number | undefined>) {
  // 以当前 URL 为基准，保证翻页/展开/返回等动作不丢筛选条件
  const query: Record<string, string> = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (typeof value === 'string' && value !== '') {
      query[key] = value
    }
  }
  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined || value === '') {
      delete query[key]
    } else {
      query[key] = String(value)
    }
  }
  return query
}

function applyFilters() {
  // 提交查询也不强制跳回第一页：沿用 URL 中保留的页码；超出范围时列表会提示
  void router.push({
    query: buildQuery({
      methodNo: draftFilters.value.methodNo.trim(),
      standardNo: draftFilters.value.standardNo.trim(),
      version: draftFilters.value.version.trim(),
      status: draftFilters.value.status,
    }),
  })
}

function resetFilters() {
  draftFilters.value = { ...EMPTY_FILTERS }
  expanded.value = new Set()
  void router.push({ query: { page: '1', size: String(size.value) } })
}

function goPage(target: number) {
  const next = Math.min(Math.max(target, 1), totalPages.value)
  if (next === page.value) {
    return
  }
  void router.push({ query: buildQuery({ page: next }) })
}

function changeSize() {
  void router.push({ query: buildQuery({ page: 1, size: size.value }) })
}

function isExpanded(no: string) {
  return expanded.value.has(no)
}

function toggleGroup(no: string) {
  const next = new Set(expanded.value)
  if (next.has(no)) {
    next.delete(no)
  } else {
    next.add(no)
  }
  expanded.value = next
}

function openDetail(id: number) {
  // 返回列表时凭该参数完整恢复筛选条件、页码与展开状态
  const back = route.fullPath
  void router.push({ name: 'method-detail', params: { id }, query: { back } })
}

function exportRows() {
  const query = new URLSearchParams()
  const filters = readFiltersFromRoute()
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      query.set(key, value)
    }
  }
  window.open(`${ENDPOINT}/export?${query.toString()}`, '_blank')
}

function openCreate() {
  errorMessage.value = '检测方法登记入口尚未接入审批流'
}

async function runAction(action: string, row: VersionRow) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '检测方法动作未生效，请稍后重试')
    }
    await loadRows()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '检测方法操作失败'
  }
}

async function loadStats() {
  try {
    const response = await request(`${ENDPOINT}/stats`)
    if (response.ok) {
      statValues.value = await response.json()
    }
  } catch {
    // 统计不阻塞列表展示
  }
}

function registerVersionRow(el: Element | ComponentPublicInstance | null) {
  const node = el as HTMLElement | null
  const id = Number(node?.dataset.versionId)
  if (!id) {
    return
  }
  if (node) {
    versionRowEls.set(id, node)
  } else {
    versionRowEls.delete(id)
  }
}

function isLocate(id: number) {
  return route.query.locate === String(id)
}

async function loadRows() {
  loading.value = true
  errorMessage.value = ''
  const filters = readFiltersFromRoute()
  draftFilters.value = filters
  const requestedSize = Number(route.query.size ?? 10)
  size.value = requestedSize === 5 ? 5 : requestedSize === 20 ? 20 : 10

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      params.set(key, value)
    }
  }
  params.set('page', String(page.value))
  params.set('size', String(size.value))

  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('检测方法列表读取失败')
    }
    const payload = (await response.json()) as { items?: MethodGroup[]; total?: number }
    rows.value = payload.items ?? []
    total.value = payload.total ?? 0
  } catch (error) {
    rows.value = []
    total.value = 0
    errorMessage.value = error instanceof Error ? error.message : '检测方法列表读取失败'
  } finally {
    loading.value = false
  }
}

async function syncExpandedAfterLoad(previousSignature: string) {
  const filters = readFiltersFromRoute()
  const signature = [filters.methodNo, filters.standardNo, filters.version, filters.status].join('|')
  const locate = typeof route.query.locate === 'string' ? route.query.locate : ''

  if (signature !== previousSignature || !filterSignature.value) {
    // 筛选条件变化：自动展开有命中版本的方法编号，重置手动展开状态
    const next = new Set<string>()
    for (const group of rows.value) {
      if (group.versions.some((version) => version.matched)) {
        next.add(group['方法编号'])
      }
    }
    expanded.value = next
  } else {
    // 只是翻页/改每页条数：清理当前页不存在的分组，保留用户的展开选择
    const visibleNos = new Set(rows.value.map((group) => group['方法编号']))
    expanded.value = new Set([...expanded.value].filter((no) => visibleNos.has(no)))
  }
  filterSignature.value = signature

  if (locate) {
    const group = rows.value.find((item) => item.versions.some((version) => String(version.id) === locate))
    if (group) {
      expanded.value = new Set([...expanded.value, group['方法编号']])
    }
    await nextTick()
    versionRowEls.get(Number(locate))?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
}

watch(
  () => route.fullPath,
  () => {
    const previous = filterSignature.value
    void loadRows().then(() => syncExpandedAfterLoad(previous))
  },
  { immediate: true },
)
void loadStats()
</script>
