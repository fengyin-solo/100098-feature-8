<template>
  <section class="page" data-module="method-detail">
    <header class="page-head">
      <div>
        <h2>检测方法详情</h2>
        <p class="page-desc">查看检测方法的完整登记信息，同一方法编号的历史版本可在下方切换定位。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="goBack">返回检测方法列表</button>
        <button class="btn" type="button" @click="locateInList">在列表中定位此版本</button>
      </div>
    </header>

    <div v-if="loading" class="detail-card">正在加载方法详情…</div>

    <div v-else-if="errorMessage" class="detail-card">
      <p class="error-text">{{ errorMessage }}</p>
      <button class="btn" type="button" @click="goBack">返回检测方法列表</button>
    </div>

    <template v-else-if="entry">
      <article class="detail-card">
        <div class="detail-title-row">
          <h3>{{ entry['方法名称'] }}</h3>
          <span class="status-badge" :class="badgeClass(entry['方法状态'])">{{ entry['方法状态'] }}</span>
        </div>
        <dl class="detail-grid">
          <div v-for="field in detailFields" :key="field" class="detail-item">
            <dt>{{ field }}</dt>
            <dd>{{ entry[field] ?? '—' }}</dd>
          </div>
          <div class="detail-item">
            <dt>记录编号</dt>
            <dd>#{{ entry.id }}</dd>
          </div>
        </dl>
        <div class="detail-actions">
          <button class="btn primary" type="button" @click="runAction('启用方法')">启用方法</button>
          <button class="btn" type="button" @click="runAction('修订方法')">修订方法</button>
          <button class="btn ghost" type="button" @click="runAction('废止方法')">废止方法</button>
          <span v-if="actionMessage" class="action-message">{{ actionMessage }}</span>
        </div>
      </article>

      <article class="detail-card">
        <h4 class="sub-title">「{{ entry['方法编号'] }}」历史版本</h4>
        <table class="data-table">
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
              v-for="version in versions"
              :key="String(version.id)"
              :class="{ 'version-current': version.id === entry.id }"
            >
              <td>{{ version['版本号'] }}</td>
              <td>{{ version['标准编号'] }}</td>
              <td>
                <span class="status-badge" :class="badgeClass(version['方法状态'])">{{ version['方法状态'] }}</span>
              </td>
              <td>
                <button v-if="version.id !== entry.id" class="link" type="button" @click="locateVersion(version.id)">
                  定位到此版本
                </button>
                <span v-else class="muted-text">当前查看版本</span>
              </td>
            </tr>
          </tbody>
        </table>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type MethodVersion = {
  id: number
  方法编号?: string
  方法名称?: string
  版本号: string
  标准编号: string
  方法状态: string
}

type MethodEntry = Record<string, string | number | boolean | null> & {
  id: number
  方法状态: string
  matched?: boolean
  同编号版本?: MethodVersion[]
}

const route = useRoute()
const router = useRouter()

const detailFields = ['方法编号', '方法名称', '标准编号', '版本号', '方法状态', '适用范围', '检出限', '精密度']

const entry = ref<MethodEntry | null>(null)
const versions = ref<MethodVersion[]>([])
const loading = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')

const entryId = computed(() => Number(route.params.id))

function badgeClass(status: string) {
  return {
    'status-active': status === '现行有效',
    'status-backup': status === '备选',
    'status-revising': status === '修订中',
    'status-revoked': status === '已废止',
  }
}

function backLocation() {
  const raw = route.query.back
  if (typeof raw === 'string' && raw.startsWith('/method')) {
    return raw
  }
  return '/method'
}

function goBack() {
  void router.push(backLocation())
}

function locateInList() {
  if (!entry.value) {
    goBack()
    return
  }
  const target = backLocation()
  const [path, rawQuery = ''] = target.split('?')
  const params = new URLSearchParams(rawQuery)
  params.set('locate', String(entry.value.id))
  void router.push(`${path}?${params.toString()}`)
}

function locateVersion(id: number) {
  const query = { ...route.query }
  void router.replace({ name: 'method-detail', params: { id }, query })
}

async function loadEntry() {
  loading.value = true
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    const response = await request(`/api/method/${entryId.value}`)
    if (response.status === 404) {
      throw new Error('该检测方法不存在或已归档')
    }
    if (!response.ok) {
      throw new Error('检测方法详情读取失败')
    }
    const payload = (await response.json()) as MethodEntry
    entry.value = payload
    // 后端已按版本号从新到旧返回同编号的全部版本
    versions.value = payload.同编号版本 ?? []
  } catch (error) {
    entry.value = null
    errorMessage.value = error instanceof Error ? error.message : '检测方法详情读取失败'
  } finally {
    loading.value = false
  }
}

async function runAction(action: string) {
  if (!entry.value) {
    return
  }
  actionMessage.value = ''
  try {
    const response = await request(`/api/method/${entry.value.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '检测方法动作未生效，请稍后重试')
    }
    actionMessage.value = payload.message || '操作已生效'
    await loadEntry()
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : '检测方法操作失败'
  }
}

watch(entryId, () => void loadEntry(), { immediate: true })
</script>
