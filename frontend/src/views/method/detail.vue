<template>
  <section class="page" data-module="method-detail">
    <header class="page-head">
      <div>
        <h2>检测方法详情</h2>
        <p class="page-desc">单份检测方法的登记信息，方法状态与台账列表读取同一份数据。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回方法台账</button>
      </div>
    </header>

    <p v-if="loading" class="empty-state">检测方法详情加载中…</p>
    <p v-else-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <template v-if="entry">
      <div class="detail-card">
        <dl class="detail-grid">
          <template v-for="field in fields" :key="field.key">
            <dt>{{ field.label }}</dt>
            <dd :class="{ 'status-strong': field.key === '方法状态' }">{{ entry[field.key] ?? '—' }}</dd>
          </template>
        </dl>
      </div>

      <div v-if="versions.length" class="detail-card">
        <h3 class="detail-subtitle">同一方法编号的历史版本</h3>
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
              v-for="item in versions"
              :key="String(item.id)"
              :class="{ 'version-current': item.id === entry?.id }"
            >
              <td>
                {{ item.版本号 }}
                <span v-if="item.id === entry?.id" class="version-tag">当前版本</span>
              </td>
              <td>{{ item.标准编号 }}</td>
              <td>{{ item.方法状态 }}</td>
              <td>
                <button
                  v-if="item.id !== entry?.id"
                  class="link"
                  type="button"
                  @click="openVersion(item)"
                >
                  切换到该版本
                </button>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/method'
const fields = [
  { label: '记录ID', key: 'id' },
  { label: '方法编号', key: '方法编号' },
  { label: '方法名称', key: '方法名称' },
  { label: '标准编号', key: '标准编号' },
  { label: '版本号', key: '版本号' },
  { label: '适用范围', key: '适用范围' },
  { label: '检出限', key: '检出限' },
  { label: '精密度', key: '精密度' },
  { label: '方法状态', key: '方法状态' },
]

const route = useRoute()
const router = useRouter()

const entry = ref<Row | null>(null)
const versions = ref<Row[]>([])
const loading = ref(false)
const errorMessage = ref('')

function goBack() {
  // 从列表进入时原路返回，地址栏里的筛选条件与页码随之恢复；直接打开详情时回台账首页
  if (window.history.state?.back) {
    router.back()
  } else {
    void router.push({ name: 'method' })
  }
}

function openVersion(item: Row) {
  void router.replace({ name: 'method-detail', params: { id: String(item.id) } })
}

async function loadEntry(id: string) {
  errorMessage.value = ''
  loading.value = true
  entry.value = null
  versions.value = []
  try {
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail ?? '检测方法详情读取失败')
    }
    entry.value = await response.json()
    const code = String(entry.value?.方法编号 ?? '')
    if (code) {
      const versionResponse = await request(`${ENDPOINT}/versions?method_code=${encodeURIComponent(code)}`)
      if (versionResponse.ok) {
        versions.value = await versionResponse.json()
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '检测方法详情读取失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string' && id) {
      void loadEntry(id)
    }
  },
)

onMounted(() => {
  void loadEntry(String(route.params.id ?? ''))
})
</script>
