<template>
  <section class="page" data-module="method">
    <header class="page-head">
      <div>
        <h2>检测方法管理</h2>
        <p class="page-desc">维护检测方法，围绕方法编号、方法名称、标准编号、适用范围做登记、筛选与状态流转。</p>
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
        <input v-model.trim="filters.methodCode" placeholder="如 METH-0001" />
      </label>
      <label class="filter-item">
        <span>标准编号</span>
        <input v-model.trim="filters.standardCode" placeholder="如 HJ 828" />
      </label>
      <label class="filter-item">
        <span>版本号</span>
        <input v-model.trim="filters.version" placeholder="如 V2.0" />
      </label>
      <label class="filter-item">
        <span>状态排序</span>
        <select v-model="statusSort">
          <option value="">默认顺序</option>
          <option value="现行有效优先">现行有效优先</option>
          <option value="备选优先">备选优先</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in rows" :key="String(row.id)">
          <tr :id="`method-row-${row.id}`" :class="{ 'row-located': locatedId === Number(row.id) }">
            <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">查看详情</button>
              <button
                v-if="Number(row.版本数) > 1"
                class="link"
                type="button"
                @click="toggleVersions(row)"
              >
                {{ expandedCode === row.方法编号 ? '收起版本' : `历史版本(${row.版本数})` }}
              </button>
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
            </td>
          </tr>
          <tr v-if="expandedCode === row.方法编号" class="version-row">
            <td :colspan="columns.length + 1">
              <div class="version-panel">
                <p class="version-title">
                  {{ row.方法编号 }} 的历史版本（共 {{ versionsOf(String(row.方法编号)).length }} 个，按版本号从新到旧）
                </p>
                <table class="version-table">
                  <thead>
                    <tr>
                      <th>版本号</th>
                      <th>标准编号</th>
                      <th>方法状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="item in versionsOf(String(row.方法编号))"
                      :key="String(item.id)"
                      :class="{ 'version-current': item.id === row.id }"
                    >
                      <td>
                        {{ item.版本号 }}
                        <span v-if="item.id === row.id" class="version-tag">当前行</span>
                      </td>
                      <td>{{ item.标准编号 }}</td>
                      <td>{{ item.方法状态 }}</td>
                      <td class="row-actions">
                        <button class="link" type="button" @click="locateVersion(item)">定位该版本</button>
                        <button class="link" type="button" @click="openDetail(item)">查看详情</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </td>
          </tr>
        </template>
        <tr v-if="loading">
          <td :colspan="columns.length + 1" class="empty-state">检测方法列表加载中…</td>
        </tr>
        <tr v-else-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">
            未检索到符合条件的检测方法。当前筛选条件已保留（{{ activeFilterText }}），可调整后重新查询或重置条件。
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条检测方法记录</span>
      <div class="pager">
        <button class="btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span>第 {{ page }} / {{ maxPage }} 页</span>
        <button class="btn" type="button" :disabled="page >= maxPage" @click="goPage(page + 1)">下一页</button>
      </div>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type StatItem = { label: string; value: number }

const ENDPOINT = '/api/method'
const columns = ["方法编号", "方法名称", "标准编号", "适用范围", "检出限", "精密度", "版本号", "方法状态"]
const actions = ["启用方法", "废止方法", "修订方法"]
const SORT_OPTIONS = ["现行有效优先", "备选优先"]
const PAGE_SIZE = 10

const route = useRoute()
const router = useRouter()

const rows = ref<Row[]>([])
const total = ref(0)
const stats = ref<StatItem[]>([])
const loading = ref(false)
const errorMessage = ref('')
// 筛选条件与页码同步到地址栏，从详情页返回时按地址栏原样恢复
const filters = ref({ methodCode: '', standardCode: '', version: '' })
const statusSort = ref('')
const page = ref(1)
const expandedCode = ref('')
const versionMap = ref<Record<string, Row[]>>({})
const locatedId = ref<number | null>(null)

const maxPage = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const activeFilterText = computed(() => {
  const parts: string[] = []
  if (filters.value.methodCode) parts.push(`方法编号「${filters.value.methodCode}」`)
  if (filters.value.standardCode) parts.push(`标准编号「${filters.value.standardCode}」`)
  if (filters.value.version) parts.push(`版本号「${filters.value.version}」`)
  if (statusSort.value) parts.push(`状态排序「${statusSort.value}」`)
  return parts.length ? parts.join('、') : '无，当前为全量列表'
})

function queryFromState(): Record<string, string> {
  const query: Record<string, string> = {}
  if (filters.value.methodCode) query.mc = filters.value.methodCode
  if (filters.value.standardCode) query.sc = filters.value.standardCode
  if (filters.value.version) query.ver = filters.value.version
  if (statusSort.value) query.sort = statusSort.value
  if (page.value > 1) query.page = String(page.value)
  return query
}

function restoreFromQuery() {
  const query = route.query
  filters.value = {
    methodCode: typeof query.mc === 'string' ? query.mc : '',
    standardCode: typeof query.sc === 'string' ? query.sc : '',
    version: typeof query.ver === 'string' ? query.ver : '',
  }
  const sort = typeof query.sort === 'string' ? query.sort : ''
  statusSort.value = SORT_OPTIONS.includes(sort) ? sort : ''
  const pageParam = Number(query.page)
  page.value = Number.isInteger(pageParam) && pageParam > 0 ? pageParam : 1
}

function versionsOf(code: string): Row[] {
  return versionMap.value[code] ?? []
}

function applyFilters() {
  // 翻页后修改条件保持在当前页；页码超出命中范围时由 reload 收拢到最后一页
  locatedId.value = null
  void reload()
}

function resetFilters() {
  filters.value = { methodCode: '', standardCode: '', version: '' }
  statusSort.value = ''
  page.value = 1
  locatedId.value = null
  void reload()
}

function goPage(target: number) {
  if (target < 1 || target > maxPage.value) return
  page.value = target
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '检测方法登记入口尚未接入审批流'
}

function openDetail(row: Row) {
  void router.push({ name: 'method-detail', params: { id: String(row.id) } })
}

async function toggleVersions(row: Row) {
  const code = String(row.方法编号 ?? '')
  if (expandedCode.value === code) {
    expandedCode.value = ''
    return
  }
  expandedCode.value = code
  if (versionMap.value[code]) return
  try {
    const response = await request(`${ENDPOINT}/versions?method_code=${encodeURIComponent(code)}`)
    if (!response.ok) {
      throw new Error('历史版本读取失败')
    }
    versionMap.value = { ...versionMap.value, [code]: await response.json() }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '历史版本读取失败'
  }
}

async function locateVersion(item: Row) {
  // 定位到指定版本：按方法编号 + 版本号组合筛选，命中后高亮对应行
  filters.value = {
    ...filters.value,
    methodCode: String(item.方法编号 ?? ''),
    version: String(item.版本号 ?? ''),
  }
  locatedId.value = Number(item.id)
  await reload()
  document.getElementById(`method-row-${item.id}`)?.scrollIntoView({ block: 'center' })
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('检测方法动作未生效，请稍后重试')
    }
    // 动作会改变方法状态，清掉已缓存的版本列表，展开时重新拉取
    versionMap.value = {}
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '检测方法操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  loading.value = true
  const params = new URLSearchParams()
  if (filters.value.methodCode) params.set('method_code', filters.value.methodCode)
  if (filters.value.standardCode) params.set('standard_code', filters.value.standardCode)
  if (filters.value.version) params.set('version', filters.value.version)
  if (statusSort.value) params.set('status_sort', statusSort.value)
  params.set('page', String(page.value))
  params.set('size', String(PAGE_SIZE))
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail ?? '检测方法列表读取失败')
    }
    const payload = await response.json()
    // 翻页后修改条件不跳回第一页；但当前页超出命中范围时收拢到最后一页，避免空白页
    if ((payload.total ?? 0) > 0 && (payload.items ?? []).length === 0 && page.value > 1) {
      page.value = Math.ceil(payload.total / PAGE_SIZE)
      await reload()
      return
    }
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    stats.value = payload.stats ?? []
    void router.replace({ query: queryFromState() })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '检测方法列表读取失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  restoreFromQuery()
  void reload()
})
</script>
