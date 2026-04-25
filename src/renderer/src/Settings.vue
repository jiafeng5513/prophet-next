<template>
  <div class="settings-page">
    <!-- 顶部栏 -->
    <div class="settings-header">
      <div class="header-left">
        <h1>系统设置</h1>
        <p class="header-desc">管理本地应用配置与 DSA 后端服务参数。</p>
      </div>
      <div class="header-actions" v-if="activeCategory !== 'local' && activeCategory !== 'dsa_service'">
        <button class="btn btn-secondary" @click="importConfig" :disabled="!dsaServerRunning || isSaving" title="从 .env 文件导入配置">导入</button>
        <button class="btn btn-secondary" @click="exportConfig" :disabled="!dsaServerRunning || dsaItems.length === 0" title="导出当前配置为 .env 文件">导出</button>
        <button class="btn btn-secondary" @click="resetDraft" :disabled="!hasDirty || isSaving">重置</button>
        <button class="btn btn-primary" @click="saveDsaBackendConfig" :disabled="!hasDirty || isSaving">
          {{ isSaving ? '保存中...' : `保存配置${dirtyCount ? ` (${dirtyCount})` : ''}` }}
        </button>
      </div>
    </div>

    <!-- 保存提示 -->
    <div class="toast-bar" v-if="toast">
      <div :class="['toast', toast.type]">{{ toast.message }}</div>
    </div>

    <!-- 主体 -->
    <div class="settings-body">
      <!-- 左侧导航 -->
      <aside class="category-nav">
        <div class="nav-group-label">本地配置</div>
        <template v-for="cat in localCategories" :key="cat.key">
          <div
            :class="['nav-item', { active: activeCategory === cat.key }]"
            @click="activeCategory = cat.key"
          >
            <span class="nav-icon">{{ cat.icon }}</span>
            <div class="nav-text">
              <div class="nav-title">{{ cat.title }}</div>
              <div class="nav-desc">{{ cat.description }}</div>
            </div>
            <span class="nav-badge" v-if="cat.count">{{ cat.count }}</span>
          </div>
        </template>
        <div class="nav-group-label">DSA 后端配置</div>
        <template v-for="cat in dsaCategories" :key="cat.key">
          <div
            :class="['nav-item', { active: activeCategory === cat.key }]"
            @click="activeCategory = cat.key"
          >
            <span class="nav-icon">{{ cat.icon }}</span>
            <div class="nav-text">
              <div class="nav-title">{{ cat.title }}</div>
              <div class="nav-desc">{{ cat.description }}</div>
            </div>
            <span class="nav-badge" v-if="cat.count">{{ cat.count }}</span>
          </div>
        </template>
      </aside>

      <!-- 右侧内容 -->
      <section class="settings-content">
        <!-- 本地设置 -->
        <template v-if="activeCategory === 'local'">
          <div class="section-card">
            <div class="section-title">应用设置</div>
            <div class="section-desc">工作区目录、主题与图表数据源配置。</div>

            <div class="field-item">
              <label>工作区目录</label>
              <div class="field-row">
                <input type="text" :value="localConfig.workspacePath" readonly class="field-input flex-1" />
                <button class="btn btn-browse" @click="browseWorkspace">浏览...</button>
              </div>
              <div class="field-desc">工作区用于存储项目文件和 Python 脚本</div>
            </div>

            <div class="field-item">
              <label>主题</label>
              <select v-model="localConfig.theme" @change="saveLocalSetting('theme', localConfig.theme)" class="field-input">
                <option value="dark">深色</option>
                <option value="light">浅色</option>
                <option value="auto">跟随系统</option>
              </select>
              <div class="field-desc">选择应用程序的主题</div>
            </div>

            <div class="field-item">
              <label>数据源</label>
              <select v-model="localConfig.dataSource" @change="onDataSourceChange" class="field-input">
                <option value="binance">Binance</option>
                <option value="okx">OKX</option>
              </select>
              <div class="field-desc">选择图表数据源，切换数据源将关闭所有已打开的图表页面</div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-title">标签页设置</div>
            <div class="section-desc">标签页行为与限制配置。</div>

            <div class="field-item">
              <label class="checkbox-row">
                <input type="checkbox" v-model="localConfig.closeWarning"
                  @change="saveLocalSetting('close-warning', localConfig.closeWarning)" />
                <span>关闭标签页时显示警告</span>
              </label>
              <div class="field-desc">关闭标签页前显示确认对话框</div>
            </div>

            <div class="field-item">
              <label>最大标签页数量</label>
              <input type="number" v-model.number="localConfig.maxTabs" min="1" max="20"
                @change="saveLocalSetting('max-tabs', localConfig.maxTabs)" class="field-input" />
              <div class="field-desc">允许同时打开的最大标签页数量</div>
            </div>
          </div>
        </template>

        <!-- DSA 服务设置 -->
        <template v-if="activeCategory === 'dsa_service'">
          <div class="section-card">
            <div class="section-title">DSA 服务连接</div>
            <div class="section-desc">后端服务已内置在项目中，使用 uv 自动管理 Python 虚拟环境与依赖。</div>

            <div class="field-item">
              <label>后端路径（内置）</label>
              <div class="field-row">
                <input type="text" :value="dsaLocal.backendPath" readonly class="field-input flex-1" />
              </div>
              <div class="field-desc">内置后端目录，由应用自动管理，无需手动修改</div>
            </div>

            <div class="field-item">
              <label>服务端口</label>
              <input type="number" v-model.number="dsaLocal.port" min="1024" max="65535"
                @change="saveDsaLocal" class="field-input" />
              <div class="field-desc">FastAPI 服务监听端口，默认 8100</div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-title">服务状态</div>
            <div class="section-desc">管理 DSA 后端服务的运行状态。</div>

            <div class="field-item">
              <div class="status-row">
                <span class="status-dot" :style="{ background: statusInfo.color }"></span>
                <span class="status-text">{{ statusInfo.text }}</span>
                <button v-if="statusInfo.showStart" class="btn btn-start" @click="startServer">启动服务</button>
                <button v-if="statusInfo.showStop" class="btn btn-stop" @click="stopServer">停止服务</button>
              </div>
              <div class="field-desc">{{ statusDesc }}</div>
            </div>
          </div>
        </template>

        <!-- DSA 后端配置分类（schema 驱动） -->
        <template v-if="isDsaCategory">
          <div v-if="!dsaServerRunning" class="empty-state">
            <div class="empty-icon">⚙️</div>
            <div class="empty-title">DSA 服务未运行</div>
            <div class="empty-desc">请先在「DSA 服务」页面启动后端服务，然后即可管理此分类的配置项。</div>
          </div>

          <div v-else-if="isLoadingDsa" class="loading-state">
            <div class="spinner"></div>
            <div>正在加载配置...</div>
          </div>

          <div v-else-if="dsaLoadError" class="error-state">
            <div class="error-title">加载失败</div>
            <div class="error-desc">{{ dsaLoadError }}</div>
            <button class="btn btn-primary" @click="loadDsaConfig">重试</button>
          </div>

          <!-- LLM 渠道编辑器 -->
          <div v-else-if="activeCategory === 'ai_model'" class="llm-editor">

            <!-- ① 快速添加渠道 -->
            <div class="llm-group">
              <div class="llm-group-title">快速添加渠道</div>
              <div class="channel-add-bar">
                <select v-model="addPresetKey" class="field-input channel-add-select">
                  <option value="">选择服务商...</option>
                  <option v-for="(p, pk) in channelPresets" :key="pk" :value="pk">{{ p.label }}</option>
                </select>
                <button class="btn btn-primary" @click="addChannelFromPreset" :disabled="!addPresetKey">+ 添加渠道</button>
                <span class="channel-count-badge" v-if="channels.length">{{ enabledChannelCount }}/{{ channels.length }} 已启用</span>
              </div>
            </div>

            <!-- ② 渠道列表 -->
            <div class="llm-group">
              <div class="llm-group-title">渠道列表</div>
              <div class="channels-wrapper" v-if="channels.length">
                <div v-for="(ch, idx) in channels" :key="idx" class="channel-card" :class="{ expanded: expandedChannels[idx] }">
                  <!-- 折叠行 -->
                  <div class="channel-row" @click="toggleChannelExpand(idx)">
                    <span class="channel-expand-arrow" :class="{ open: expandedChannels[idx] }">▶</span>
                    <label class="channel-enable-check" @click.stop>
                      <input type="checkbox" v-model="ch.enabled" @change="markChannelsDirty" />
                    </label>
                    <span class="channel-row-name">{{ ch.name || '未命名渠道' }}</span>
                    <span class="channel-row-badge">{{ protocolLabel(ch.protocol) }}</span>
                    <span class="channel-row-models">{{ channelModelCount(ch) }}个模型</span>
                    <span class="channel-status-dot" :class="channelStatusClass(ch)"></span>
                    <span v-if="!ch.apiKey" class="channel-row-warn">未填 Key</span>
                    <button class="btn btn-icon btn-danger-icon channel-row-delete" @click.stop="removeChannel(idx)" title="删除渠道">✕</button>
                  </div>
                  <!-- 展开区 -->
                  <div v-show="expandedChannels[idx]" class="channel-body">
                    <div class="channel-field">
                      <label>渠道名称</label>
                      <input type="text" v-model="ch.name" class="field-input" placeholder="如 my_deepseek" @change="markChannelsDirty" />
                    </div>
                    <div class="channel-field">
                      <label>协议</label>
                      <select v-model="ch.protocol" class="field-input" @change="markChannelsDirty">
                        <option v-for="po in protocolOptions" :key="po.value" :value="po.value">{{ po.label }}</option>
                      </select>
                    </div>
                    <div class="channel-field">
                      <label>Base URL</label>
                      <input type="text" v-model="ch.baseUrl" class="field-input" placeholder="留空使用默认" @change="markChannelsDirty" />
                    </div>
                    <div class="channel-field">
                      <label>API Key</label>
                      <div class="field-row">
                        <input :type="ch.showKey ? 'text' : 'password'" v-model="ch.apiKey"
                          class="field-input flex-1" placeholder="输入 API Key" @change="markChannelsDirty" />
                        <button class="btn btn-browse" @click="ch.showKey = !ch.showKey">{{ ch.showKey ? '隐藏' : '显示' }}</button>
                      </div>
                    </div>
                    <div class="channel-field">
                      <label>模型列表</label>
                      <input type="text" v-model="ch.models" class="field-input"
                        :placeholder="channelPresets[ch.preset]?.placeholder || 'model-1,model-2'" @change="markChannelsDirty" />
                      <div class="field-desc">逗号分隔的模型名称</div>
                    </div>
                    <div class="channel-actions">
                      <button class="btn btn-secondary" @click="discoverModels(idx)"
                        :disabled="ch.discovering || !ch.apiKey || !ch.name">
                        {{ ch.discovering ? '发现中...' : '获取模型' }}
                      </button>
                      <button class="btn btn-secondary" @click="testChannel(idx)"
                        :disabled="ch.testing || !ch.apiKey || !ch.name">
                        {{ ch.testing ? '测试中...' : '测试连接' }}
                      </button>
                      <span v-if="ch.testResult" :class="['test-result', ch.testResult.ok ? 'success' : 'error']">
                        {{ ch.testResult.message }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="channel-empty-hint">暂无渠道，请在上方选择服务商添加。</div>
            </div>

            <!-- ③ 运行时参数 -->
            <div class="llm-group">
              <div class="llm-group-title">运行时参数</div>
              <div class="runtime-params-list">
                <!-- 分析主模型 -->
                <div class="field-item">
                  <div class="field-label-row"><label>分析主模型</label></div>
                  <select :value="getDraftValue('LITELLM_MODEL')"
                    @change="setDraft('LITELLM_MODEL', $event.target.value)"
                    class="field-input">
                    <option value="">自动（使用第一个可用模型）</option>
                    <option v-for="m in allChannelModels" :key="m.value" :value="m.value">{{ m.label }}</option>
                  </select>
                  <div class="field-desc">分析和对话使用的默认模型。自动模式下按渠道优先级选取第一个可用模型。</div>
                </div>
                <!-- Agent 主模型 -->
                <div class="field-item">
                  <div class="field-label-row"><label>Agent 主模型</label></div>
                  <select :value="getDraftValue('AGENT_LITELLM_MODEL')"
                    @change="setDraft('AGENT_LITELLM_MODEL', $event.target.value)"
                    class="field-input">
                    <option value="">自动（继承分析主模型）</option>
                    <option v-for="m in allChannelModels" :key="m.value" :value="m.value">{{ m.label }}</option>
                  </select>
                  <div class="field-desc">Agent 专用模型。自动模式下直接使用分析主模型。</div>
                </div>
                <!-- 备选模型（多选） -->
                <div class="field-item">
                  <div class="field-label-row"><label>备选模型</label></div>
                  <div class="fallback-model-list" v-if="allChannelModels.length">
                    <label v-for="m in allChannelModels" :key="m.value" class="fallback-model-option">
                      <input type="checkbox"
                        :checked="isFallbackSelected(m.value)"
                        @change="toggleFallbackModel(m.value, $event.target.checked)" />
                      <span>{{ m.label }}</span>
                    </label>
                  </div>
                  <div v-else class="field-desc" style="color:#666;">请先在渠道中配置模型</div>
                  <div class="field-desc">主模型失败时按勾选顺序依次尝试</div>
                </div>
                <!-- Vision 模型 -->
                <div class="field-item">
                  <div class="field-label-row"><label>Vision 模型</label></div>
                  <select :value="getDraftValue('VISION_MODEL')"
                    @change="setDraft('VISION_MODEL', $event.target.value)"
                    class="field-input">
                    <option value="">自动（跟随 Vision 默认逻辑）</option>
                    <option v-for="m in allChannelModels" :key="m.value" :value="m.value">{{ m.label }}</option>
                  </select>
                  <div class="field-desc">图片理解专用模型。自动模式下优先使用分析主模型，再按 Gemini → Anthropic → OpenAI 推断。</div>
                </div>
              </div>
              <!-- Temperature 滑动条 -->
              <div class="field-item temperature-field">
                <div class="field-label-row">
                  <label>Temperature</label>
                  <span class="temperature-value">{{ temperatureDisplay }}</span>
                </div>
                <input type="range" min="0" max="2" step="0.1"
                  :value="getDraftValue('LLM_TEMPERATURE') || '0.7'"
                  @input="setDraft('LLM_TEMPERATURE', $event.target.value)"
                  class="temperature-slider" />
                <div class="temperature-labels">
                  <span>精确 (0)</span>
                  <span>平衡 (1)</span>
                  <span>创意 (2)</span>
                </div>
              </div>
            </div>

            <!-- ④ 高级路由配置 -->
            <div class="llm-group">
              <div class="llm-group-title">高级路由配置</div>
              <div class="field-item">
                <div class="field-label-row"><label>高级模型路由 YAML 配置文件路径</label></div>
                <input type="text" :value="getDraftValue('LITELLM_CONFIG')"
                  @input="setDraft('LITELLM_CONFIG', $event.target.value)"
                  class="field-input" placeholder="如 /path/to/litellm_config.yaml" />
                <div class="field-desc">指定 LiteLLM 路由配置文件。配置此项后将使用高级路由模式。</div>
              </div>
            </div>

            <!-- 保存按钮 -->
            <div class="channel-save-row" v-if="channelsDirty">
              <button class="btn btn-primary" @click="saveChannels" :disabled="isSavingChannels">
                {{ isSavingChannels ? '保存中...' : '保存 AI 配置' }}
              </button>
            </div>
          </div>

          <!-- 通用 schema 字段列表（ai_model 已由专用编辑器处理） -->
          <div v-if="dsaServerRunning && !isLoadingDsa && !dsaLoadError && filteredActiveItems.length && activeCategory !== 'ai_model'" class="section-card">
            <div class="section-title">{{ currentCategoryTitle }}</div>
            <div class="section-desc">{{ currentCategoryDesc }}</div>

            <div v-for="item in filteredActiveItems" :key="item.key" class="field-item">
              <div class="field-label-row">
                <label>{{ getFieldTitle(item.key, item.schema?.title) }}</label>
                <span v-if="item.schema?.isSensitive" class="badge sensitive">敏感</span>
                <span v-if="item.schema && !item.schema.isEditable" class="badge readonly">只读</span>
              </div>

              <!-- switch -->
              <label v-if="item.schema?.uiControl === 'switch'" class="checkbox-row">
                <input type="checkbox" :checked="getDraftValue(item.key) === 'true'"
                  @change="setDraft(item.key, $event.target.checked ? 'true' : 'false')"
                  :disabled="item.schema && !item.schema.isEditable" />
                <span>{{ getDraftValue(item.key) === 'true' ? '已启用' : '已禁用' }}</span>
              </label>

              <!-- select -->
              <select v-else-if="item.schema?.uiControl === 'select'"
                :value="getDraftValue(item.key)"
                @change="setDraft(item.key, $event.target.value)"
                class="field-input"
                :disabled="item.schema && !item.schema.isEditable">
                <option value="">-- 请选择 --</option>
                <option v-for="opt in normalizeOptions(item.schema?.options)" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>

              <!-- textarea -->
              <textarea v-else-if="item.schema?.uiControl === 'textarea'"
                :value="getDraftValue(item.key)"
                @input="setDraft(item.key, $event.target.value)"
                class="field-input field-textarea"
                :disabled="item.schema && !item.schema.isEditable"
                rows="3"></textarea>

              <!-- password -->
              <div v-else-if="item.schema?.uiControl === 'password'" class="field-row">
                <input :type="passwordVisibility[item.key] ? 'text' : 'password'"
                  :value="getDraftValue(item.key)"
                  @input="setDraft(item.key, $event.target.value)"
                  class="field-input flex-1"
                  :placeholder="item.schema?.defaultValue || ''"
                  :disabled="item.schema && !item.schema.isEditable" />
                <button class="btn btn-browse" @click="togglePasswordVisibility(item.key)">
                  {{ passwordVisibility[item.key] ? '隐藏' : '显示' }}
                </button>
              </div>

              <!-- number -->
              <input v-else-if="item.schema?.uiControl === 'number'"
                type="number"
                :value="getDraftValue(item.key)"
                @input="setDraft(item.key, $event.target.value)"
                class="field-input"
                :min="item.schema?.validation?.min"
                :max="item.schema?.validation?.max"
                :step="item.schema?.dataType === 'number' ? 0.1 : 1"
                :disabled="item.schema && !item.schema.isEditable" />

              <!-- time -->
              <input v-else-if="item.schema?.uiControl === 'time'"
                type="time"
                :value="getDraftValue(item.key)"
                @input="setDraft(item.key, $event.target.value)"
                class="field-input"
                :disabled="item.schema && !item.schema.isEditable" />

              <!-- default text -->
              <input v-else
                type="text"
                :value="getDraftValue(item.key)"
                @input="setDraft(item.key, $event.target.value)"
                class="field-input"
                :placeholder="item.schema?.defaultValue || ''"
                :disabled="item.schema && !item.schema.isEditable" />

              <div class="field-desc">{{ getFieldDesc(item.key, item.schema?.description) }}</div>
            </div>
          </div>

          <div v-else-if="dsaServerRunning && !isLoadingDsa && !dsaLoadError && filteredActiveItems.length === 0 && activeCategory !== 'ai_model'" class="empty-state">
            <div class="empty-title">当前分类下暂无配置项</div>
            <div class="empty-desc">可切换左侧分类继续查看其它系统配置。</div>
          </div>
        </template>
      </section>
    </div>

    <!-- 确认对话框 -->
    <div v-if="confirmDialog.show" class="dialog-overlay" @click.self="confirmDialog.onCancel">
      <div class="dialog-box">
        <h3>{{ confirmDialog.title }}</h3>
        <p>{{ confirmDialog.message }}</p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" @click="confirmDialog.onCancel">{{ confirmDialog.cancelText }}</button>
          <button class="btn btn-primary" @click="confirmDialog.onConfirm">{{ confirmDialog.confirmText }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'

// =============================
// i18n 翻译
// =============================
const categoryTitleMap = {
  base: '基础设置',
  data_source: '数据源',
  ai_model: 'AI 模型',
  notification: '通知渠道',
  system: '系统设置',
  agent: 'Agent 设置',
  backtest: '回测配置',
  uncategorized: '其他',
}
const categoryDescMap = {
  base: '管理自选股与基础运行参数。',
  data_source: '管理行情数据源与优先级策略。',
  ai_model: '管理模型供应商、模型名称与推理参数。',
  notification: '管理机器人、Webhook 和消息推送配置。',
  system: '管理调度、日志、端口等系统级参数。',
  agent: '管理 Agent 模式、策略与多 Agent 编排配置。',
  backtest: '管理回测开关、评估窗口和引擎参数。',
  uncategorized: '其他未归类的配置项。',
}
const fieldTitleMap = {
  STOCK_LIST: '自选股列表',
  TUSHARE_TOKEN: 'Tushare Token',
  TICKFLOW_API_KEY: 'TickFlow API Key',
  BOCHA_API_KEYS: 'Bocha API Keys',
  TAVILY_API_KEYS: 'Tavily API Keys',
  ANSPIRE_API_KEYS: 'Anspire API Keys',
  SERPAPI_API_KEYS: 'SerpAPI API Keys',
  BRAVE_API_KEYS: 'Brave API Keys',
  SEARXNG_BASE_URLS: 'SearXNG Base URLs',
  SEARXNG_PUBLIC_INSTANCES_ENABLED: 'SearXNG 公共实例自动发现',
  MINIMAX_API_KEYS: 'MiniMax API Keys',
  NEWS_STRATEGY_PROFILE: '新闻策略窗口档位',
  NEWS_MAX_AGE_DAYS: '新闻最大时效（天）',
  REALTIME_SOURCE_PRIORITY: '实时数据源优先级',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '盘中实时技术面',
  ENABLE_REALTIME_QUOTE: '启用实时行情',
  ENABLE_CHIP_DISTRIBUTION: '启用筹码分布',
  BIAS_THRESHOLD: '偏离阈值 (%)',
  PYTDX_HOST: 'Pytdx 服务器',
  PYTDX_PORT: 'Pytdx 端口',
  PYTDX_SERVERS: 'Pytdx 服务器列表',
  LITELLM_MODEL: '主模型',
  AGENT_LITELLM_MODEL: 'Agent 主模型',
  LITELLM_FALLBACK_MODELS: '备选模型',
  LITELLM_CONFIG: '高级模型路由配置',
  LLM_CHANNELS: 'LLM 渠道列表',
  LLM_TEMPERATURE: '采样温度',
  AIHUBMIX_KEY: 'AIHubmix Key',
  DEEPSEEK_API_KEY: 'DeepSeek API Key',
  DEEPSEEK_API_KEYS: 'DeepSeek API Keys (Multi)',
  GEMINI_API_KEY: 'Gemini API Key',
  GEMINI_API_KEYS: 'Gemini API Keys (Multi)',
  GEMINI_MODEL: 'Gemini 模型',
  GEMINI_MODEL_FALLBACK: 'Gemini 备选模型',
  GEMINI_TEMPERATURE: 'Gemini 温度参数',
  ANTHROPIC_API_KEY: 'Anthropic API Key',
  ANTHROPIC_API_KEYS: 'Anthropic API Keys (Multi)',
  ANTHROPIC_MODEL: 'Anthropic 模型',
  ANTHROPIC_TEMPERATURE: 'Anthropic 温度',
  ANTHROPIC_MAX_TOKENS: 'Anthropic Max Tokens',
  OPENAI_API_KEY: 'OpenAI API Key',
  OPENAI_API_KEYS: 'OpenAI API Keys (Multi)',
  OPENAI_BASE_URL: 'OpenAI Base URL',
  OPENAI_MODEL: 'OpenAI 模型',
  OPENAI_VISION_MODEL: 'OpenAI 视觉模型',
  OPENAI_TEMPERATURE: 'OpenAI 温度',
  VISION_MODEL: '视觉模型',
  WECHAT_WEBHOOK_URL: '企业微信 Webhook',
  FEISHU_WEBHOOK_URL: '飞书群机器人 Webhook',
  FEISHU_WEBHOOK_SECRET: '飞书 Webhook 签名密钥',
  FEISHU_WEBHOOK_KEYWORD: '飞书 Webhook 关键词',
  FEISHU_APP_ID: '飞书应用 App ID',
  FEISHU_APP_SECRET: '飞书应用 App Secret',
  DINGTALK_APP_KEY: '钉钉 App Key',
  DINGTALK_APP_SECRET: '钉钉 App Secret',
  PUSHPLUS_TOKEN: 'PushPlus Token',
  REPORT_SUMMARY_ONLY: '仅分析结果摘要',
  MAX_WORKERS: '最大并发线程数',
  SCHEDULE_TIME: '定时任务时间',
  HTTP_PROXY: 'HTTP 代理',
  LOG_LEVEL: '日志级别',
  WEBUI_PORT: 'WebUI 端口',
  ADMIN_AUTH_ENABLED: '启用管理认证',
  AGENT_MODE: '启用 Agent 策略问股',
  AGENT_MAX_STEPS: 'Agent 最大步数',
  AGENT_SKILLS: 'Agent 激活策略',
  AGENT_SKILL_DIR: 'Agent 策略目录',
  AGENT_ARCH: 'Agent 架构模式',
  AGENT_ORCHESTRATOR_MODE: '编排模式',
  AGENT_ORCHESTRATOR_TIMEOUT_S: 'Agent 超时（秒）',
  AGENT_RISK_OVERRIDE: '风控 Agent 否决',
  AGENT_SKILL_AUTOWEIGHT: '策略自动加权',
  AGENT_SKILL_ROUTING: '策略路由模式',
  AGENT_MEMORY_ENABLED: '记忆与校准',
  BACKTEST_ENABLED: '启用回测',
  BACKTEST_EVAL_WINDOW_DAYS: '回测评估窗口（交易日）',
  BACKTEST_MIN_AGE_DAYS: '回测最小历史天数',
  BACKTEST_ENGINE_VERSION: '回测引擎版本',
  BACKTEST_NEUTRAL_BAND_PCT: '回测中性区间阈值（%）',
  // 报告配置
  REPORT_TYPE: '报告类型',
  REPORT_LANGUAGE: '报告语言',
  REPORT_TEMPLATES_DIR: '报告模板目录',
  REPORT_RENDERER_ENABLED: '启用报告渲染',
  REPORT_INTEGRITY_ENABLED: '报告完整性校验',
  REPORT_INTEGRITY_RETRY: '完整性校验重试次数',
  REPORT_HISTORY_COMPARE_N: '历史对比报告数',
  // Telegram
  TELEGRAM_BOT_TOKEN: 'Telegram Bot Token',
  TELEGRAM_CHAT_ID: 'Telegram Chat ID',
  TELEGRAM_MESSAGE_THREAD_ID: 'Telegram 消息线程 ID',
  TELEGRAM_WEBHOOK_SECRET: 'Telegram Webhook Secret',
  // Email
  EMAIL_SENDER: '发件人邮箱',
  EMAIL_SENDER_NAME: '发件人名称',
  EMAIL_PASSWORD: '邮箱密码/授权码',
  EMAIL_RECEIVERS: '收件人列表',
  // Discord
  DISCORD_BOT_TOKEN: 'Discord Bot Token',
  DISCORD_BOT_STATUS: 'Discord Bot 状态',
  DISCORD_MAIN_CHANNEL_ID: 'Discord 主频道 ID',
  DISCORD_WEBHOOK_URL: 'Discord Webhook URL',
  DISCORD_INTERACTIONS_PUBLIC_KEY: 'Discord 交互公钥',
  // Slack
  SLACK_WEBHOOK_URL: 'Slack Webhook URL',
  SLACK_BOT_TOKEN: 'Slack Bot Token',
  SLACK_CHANNEL_ID: 'Slack 频道 ID',
  // 飞书扩展
  FEISHU_VERIFICATION_TOKEN: '飞书验证 Token',
  FEISHU_ENCRYPT_KEY: '飞书加密密钥',
  FEISHU_STREAM_ENABLED: '飞书事件流模式',
  FEISHU_FOLDER_TOKEN: '飞书文档目录 Token',
  FEISHU_MAX_BYTES: '飞书消息最大字节',
  // 钉钉扩展
  DINGTALK_STREAM_ENABLED: '钉钉事件流模式',
  // 企业微信扩展
  WECOM_CORPID: '企业微信 Corp ID',
  WECOM_TOKEN: '企业微信 Token',
  WECOM_ENCODING_AES_KEY: '企业微信加密密钥',
  WECOM_AGENT_ID: '企业微信 Agent ID',
  WECHAT_MAX_BYTES: '微信消息最大字节',
  WECHAT_MSG_TYPE: '微信消息类型',
  // PushPlus / PushOver / ServerChan
  PUSHPLUS_TOPIC: 'PushPlus 话题',
  PUSHOVER_USER_KEY: 'Pushover User Key',
  PUSHOVER_API_TOKEN: 'Pushover API Token',
  SERVERCHAN3_SENDKEY: 'Server酱 SendKey',
  // 自定义 Webhook
  CUSTOM_WEBHOOK_URLS: '自定义 Webhook URLs',
  CUSTOM_WEBHOOK_BEARER_TOKEN: 'Webhook Bearer Token',
  WEBHOOK_VERIFY_SSL: 'Webhook 验证 SSL',
  // AstrBot
  ASTRBOT_TOKEN: 'AstrBot Token',
  ASTRBOT_URL: 'AstrBot URL',
  // 通知行为
  SINGLE_STOCK_NOTIFY: '单股通知模式',
  ANALYSIS_DELAY: '分析延迟（秒）',
  MERGE_EMAIL_NOTIFICATION: '合并邮件通知',
  MARKDOWN_TO_IMAGE_CHANNELS: 'MD 转图渠道',
  MARKDOWN_TO_IMAGE_MAX_CHARS: 'MD 转图最大字符数',
  MD2IMG_ENGINE: 'MD 转图引擎',
  DISCORD_MAX_WORDS: 'Discord 最大字数',
  // Longbridge 数据源
  LONGBRIDGE_APP_KEY: 'Longbridge App Key',
  LONGBRIDGE_APP_SECRET: 'Longbridge App Secret',
  LONGBRIDGE_ACCESS_TOKEN: 'Longbridge Access Token',
  // 实时数据扩展
  ENABLE_EASTMONEY_PATCH: '东方财富增强',
  REALTIME_CACHE_TTL: '实时缓存 TTL（秒）',
  CIRCUIT_BREAKER_COOLDOWN: '熔断冷却（秒）',
  PREFETCH_REALTIME_QUOTES: '预取实时行情',
  // 基本面管线
  ENABLE_FUNDAMENTAL_PIPELINE: '启用基本面管线',
  FUNDAMENTAL_STAGE_TIMEOUT_SECONDS: '阶段超时（秒）',
  FUNDAMENTAL_FETCH_TIMEOUT_SECONDS: '请求超时（秒）',
  FUNDAMENTAL_RETRY_MAX: '最大重试次数',
  FUNDAMENTAL_CACHE_TTL_SECONDS: '缓存 TTL（秒）',
  FUNDAMENTAL_CACHE_MAX_ENTRIES: '最大缓存条数',
  // 组合风控
  PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT: '集中度预警(%)',
  PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT: '回撤预警(%)',
  PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT: '止损预警(%)',
  PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO: '止损接近比率',
  PORTFOLIO_RISK_LOOKBACK_DAYS: '风控回看天数',
  PORTFOLIO_FX_UPDATE_ENABLED: '外汇更新',
  // Agent 扩展
  AGENT_NL_ROUTING: '自然语言路由',
  AGENT_DEEP_RESEARCH_BUDGET: '深度研究 Token 预算',
  AGENT_DEEP_RESEARCH_TIMEOUT: '深度研究超时（秒）',
  AGENT_EVENT_MONITOR_ENABLED: '事件监控',
  AGENT_EVENT_MONITOR_INTERVAL_MINUTES: '监控间隔（分钟）',
  AGENT_EVENT_ALERT_RULES_JSON: '事件告警规则 JSON',
  // 视觉模型
  VISION_PROVIDER_PRIORITY: '视觉模型优先级',
  // Gemini 扩展
  GEMINI_REQUEST_DELAY: 'Gemini 请求间隔（秒）',
  GEMINI_MAX_RETRIES: 'Gemini 最大重试',
  GEMINI_RETRY_DELAY: 'Gemini 重试延迟（秒）',
  // 社交情绪
  SOCIAL_SENTIMENT_API_KEY: '社交情绪 API Key',
  SOCIAL_SENTIMENT_API_URL: '社交情绪 API URL',
  // 调度扩展
  SCHEDULE_ENABLED: '启用定时任务',
  SCHEDULE_RUN_IMMEDIATELY: '启动时立即执行',
  RUN_IMMEDIATELY: '立即运行一次',
  MARKET_REVIEW_ENABLED: '市场复盘',
  MARKET_REVIEW_REGION: '市场复盘区域',
  TRADING_DAY_CHECK_ENABLED: '交易日检查',
  // 系统扩展
  HTTPS_PROXY: 'HTTPS 代理',
  LOG_DIR: '日志目录',
  DEBUG: '调试模式',
  ADMIN_AUTH_ENABLED: '启用管理认证',
  DATABASE_PATH: '数据库路径',
  CONFIG_VALIDATE_MODE: '配置验证模式',
  PYTDX_HOST: 'Pytdx 服务器',
  PYTDX_PORT: 'Pytdx 端口',
  PYTDX_SERVERS: 'Pytdx 服务器列表',
}
const fieldDescMap = {
  STOCK_LIST: '使用逗号分隔股票代码，例如：600519,300750。',
  TUSHARE_TOKEN: '用于接入 Tushare Pro 数据服务的凭据。',
  TICKFLOW_API_KEY: '用于 TickFlow 行情增强的密钥（A 股指数+市场统计）。',
  BOCHA_API_KEYS: '用于新闻检索的 Bocha 密钥，支持逗号分隔多个（最高优先级）。',
  TAVILY_API_KEYS: '用于新闻检索的 Tavily 密钥，支持逗号分隔多个。',
  ANSPIRE_API_KEYS: '用于新闻检索的 Anspire 密钥，支持逗号分隔多个。',
  SERPAPI_API_KEYS: '用于新闻检索的 SerpAPI 密钥，支持逗号分隔多个。',
  BRAVE_API_KEYS: '用于新闻检索的 Brave Search 密钥，支持逗号分隔多个。',
  SEARXNG_BASE_URLS: 'SearXNG 自建实例地址（逗号分隔，无配额兜底）。',
  SEARXNG_PUBLIC_INSTANCES_ENABLED: '当未配置 SearXNG 自建实例时，自动从 searx.space 获取公共实例并轮询使用。',
  MINIMAX_API_KEYS: '用于新闻检索的 MiniMax 密钥，支持逗号分隔多个（最低优先级）。',
  NEWS_STRATEGY_PROFILE: '新闻窗口档位：ultra_short=1天，short=3天，medium=7天，long=30天。',
  NEWS_MAX_AGE_DAYS: '新闻最大时效上限。实际窗口 = min(策略档位天数, NEWS_MAX_AGE_DAYS)。',
  REALTIME_SOURCE_PRIORITY: '按逗号分隔填写数据源调用优先级。',
  ENABLE_REALTIME_TECHNICAL_INDICATORS: '盘中分析时用实时价计算 MA5/MA10/MA20 与多头排列；关闭则用昨日收盘。',
  ENABLE_REALTIME_QUOTE: '启用实时行情，关闭后仅使用历史收盘价。',
  ENABLE_CHIP_DISTRIBUTION: '启用筹码分布分析。可能不稳定，建议云部署关闭。',
  BIAS_THRESHOLD: 'MA5 偏离阈值(%)，超过时触发"不追高"警告。',
  LITELLM_MODEL: '主模型，格式 provider/model（如 gemini/gemini-2.5-flash）。配置渠道后自动推断。',
  AGENT_LITELLM_MODEL: 'Agent 专用主模型。留空时继承主模型。',
  LITELLM_FALLBACK_MODELS: '备选模型，逗号分隔，主模型失败时按序尝试。',
  LLM_CHANNELS: '渠道名称列表（逗号分隔）。推荐使用上方渠道编辑器管理。',
  LLM_TEMPERATURE: '控制模型输出随机性，0 为确定性输出，2 为最大随机性，推荐 0.7。',
  AIHUBMIX_KEY: 'AIHubmix 一站式密钥，自动指向 aihubmix.com/v1。',
  DEEPSEEK_API_KEY: 'DeepSeek 官方 API 密钥。填写后自动使用 deepseek-chat 模型。',
  WECHAT_WEBHOOK_URL: '企业微信机器人 Webhook 地址。',
  FEISHU_WEBHOOK_URL: '飞书自定义机器人 Webhook。',
  FEISHU_WEBHOOK_SECRET: '飞书群机器人安全设置里的"签名校验"密钥。',
  FEISHU_WEBHOOK_KEYWORD: '飞书群机器人安全设置里的"关键词"。',
  DINGTALK_APP_KEY: '钉钉应用模式 App Key。',
  DINGTALK_APP_SECRET: '钉钉应用模式 App Secret。',
  PUSHPLUS_TOKEN: 'PushPlus 推送令牌。',
  REPORT_SUMMARY_ONLY: '仅推送分析结果摘要，不包含个股详情。',
  MAX_WORKERS: '异步任务队列最大并发数。',
  SCHEDULE_TIME: '每日定时任务执行时间，格式为 HH:MM。',
  HTTP_PROXY: '网络代理地址，可留空。',
  LOG_LEVEL: '设置日志输出级别。',
  WEBUI_PORT: 'Web 页面服务监听端口。',
  AGENT_MODE: '是否启用 ReAct Agent 策略问股。',
  AGENT_MAX_STEPS: 'Agent 最大推理步数上限。',
  AGENT_SKILLS: '逗号分隔的交易策略列表。留空使用默认策略，填 all 启用全部。',
  AGENT_SKILL_DIR: '存放 Agent 策略定义文件的目录路径。',
  AGENT_ARCH: 'Agent 执行架构。single 为经典单 Agent；multi 为多 Agent 编排。',
  AGENT_ORCHESTRATOR_MODE: 'Multi-Agent 编排深度。quick/standard/full/specialist。',
  AGENT_ORCHESTRATOR_TIMEOUT_S: 'Agent 执行总超时预算（秒），0 表示不限制。',
  AGENT_RISK_OVERRIDE: '允许风控 Agent 在发现关键风险时否决买入信号。',
  AGENT_SKILL_AUTOWEIGHT: '根据回测表现自动调整策略权重。',
  AGENT_SKILL_ROUTING: '策略选择方式。auto 按市场状态自动选择，manual 使用 AGENT_SKILLS 列表。',
  AGENT_MEMORY_ENABLED: '启用记忆与校准系统，追踪历史分析准确率并自动调节置信度。',
  BACKTEST_ENABLED: '是否启用回测功能（true/false）。',
  BACKTEST_EVAL_WINDOW_DAYS: '回测评估窗口长度，单位为交易日。',
  BACKTEST_MIN_AGE_DAYS: '仅回测早于该天数的分析记录。',
  BACKTEST_ENGINE_VERSION: '回测引擎版本标识，用于区分结果版本。',
  BACKTEST_NEUTRAL_BAND_PCT: '中性区间阈值百分比，例如 2 表示 -2%~+2%。',
  // 报告
  REPORT_TYPE: '默认报告类型：brief / detailed。',
  REPORT_LANGUAGE: '报告语言：zh（中文） / en（英文） / auto（自动检测）。',
  REPORT_TEMPLATES_DIR: '自定义 Jinja2 报告模板所在目录。',
  REPORT_RENDERER_ENABLED: '启用服务端报告渲染器。',
  REPORT_INTEGRITY_ENABLED: '启用报告完整性校验，确保关键字段不为空。',
  REPORT_INTEGRITY_RETRY: '完整性校验失败时的最大重试次数。',
  REPORT_HISTORY_COMPARE_N: '生成报告时对比的历史报告数量。',
  // Telegram
  TELEGRAM_BOT_TOKEN: 'Telegram Bot Token，从 @BotFather 获取。',
  TELEGRAM_CHAT_ID: '目标 Chat ID（群组或个人）。',
  TELEGRAM_MESSAGE_THREAD_ID: '话题群组的线程 ID（可选）。',
  TELEGRAM_WEBHOOK_SECRET: 'Telegram Webhook 回调签名密钥。',
  // Email
  EMAIL_SENDER: '发件人邮箱地址。',
  EMAIL_SENDER_NAME: '邮件显示的发件人名称。',
  EMAIL_PASSWORD: 'SMTP 授权码或邮箱密码。',
  EMAIL_RECEIVERS: '收件人邮箱列表，逗号分隔。',
  // Discord
  DISCORD_BOT_TOKEN: 'Discord Bot Token，从 Developer Portal 获取。',
  DISCORD_WEBHOOK_URL: 'Discord 频道 Webhook URL。',
  // Slack
  SLACK_WEBHOOK_URL: 'Slack Incoming Webhook URL。',
  SLACK_BOT_TOKEN: 'Slack Bot OAuth Token。',
  SLACK_CHANNEL_ID: '目标 Slack 频道 ID。',
  // 飞书扩展
  FEISHU_VERIFICATION_TOKEN: '飞书事件回调验证 Token。',
  FEISHU_ENCRYPT_KEY: '飞书事件订阅加密密钥。',
  FEISHU_STREAM_ENABLED: '启用飞书长连接事件流模式。',
  FEISHU_FOLDER_TOKEN: '飞书云文档目标文件夹 Token。',
  FEISHU_MAX_BYTES: '飞书单条消息最大字节数。',
  // 钉钉
  DINGTALK_STREAM_ENABLED: '启用钉钉 Stream 事件流模式。',
  // 企业微信
  WECOM_CORPID: '企业微信企业 ID。',
  WECOM_TOKEN: '企业微信应用回调 Token。',
  WECOM_ENCODING_AES_KEY: '企业微信应用回调加密密钥。',
  WECOM_AGENT_ID: '企业微信应用 Agent ID。',
  WECHAT_MAX_BYTES: '微信消息最大字节数。',
  WECHAT_MSG_TYPE: '微信消息格式：text / markdown。',
  // PushPlus / PushOver / ServerChan
  PUSHPLUS_TOPIC: 'PushPlus 群组推送话题 ID。',
  PUSHOVER_USER_KEY: 'Pushover User Key，从 Dashboard 获取。',
  PUSHOVER_API_TOKEN: 'Pushover Application API Token。',
  SERVERCHAN3_SENDKEY: 'Server酱 V3 SendKey。',
  // 自定义 Webhook
  CUSTOM_WEBHOOK_URLS: '自定义 Webhook 地址，逗号分隔。',
  CUSTOM_WEBHOOK_BEARER_TOKEN: '自定义 Webhook Bearer Token 认证。',
  WEBHOOK_VERIFY_SSL: '发送 Webhook 时是否验证 SSL 证书。',
  // AstrBot
  ASTRBOT_TOKEN: 'AstrBot 认证 Token。',
  ASTRBOT_URL: 'AstrBot 服务地址。',
  // 通知行为
  SINGLE_STOCK_NOTIFY: '启用后每只股票单独发送一条通知。',
  ANALYSIS_DELAY: '每支股票分析之间的延迟（秒）。',
  MERGE_EMAIL_NOTIFICATION: '将多只股票分析合并为一封邮件发送。',
  MARKDOWN_TO_IMAGE_CHANNELS: '自动将 Markdown 转为图片的通知渠道列表。',
  MARKDOWN_TO_IMAGE_MAX_CHARS: '超过此字符数时自动转为图片。',
  MD2IMG_ENGINE: 'Markdown 转图引擎：playwright / imgkit。',
  DISCORD_MAX_WORDS: 'Discord 单条消息最大字数限制。',
  // Longbridge
  LONGBRIDGE_APP_KEY: 'Longbridge OpenAPI App Key。',
  LONGBRIDGE_APP_SECRET: 'Longbridge OpenAPI App Secret。',
  LONGBRIDGE_ACCESS_TOKEN: 'Longbridge OpenAPI Access Token。',
  // 实时数据扩展
  ENABLE_EASTMONEY_PATCH: '启用东方财富增强数据补丁。',
  REALTIME_CACHE_TTL: '实时行情缓存有效期（秒）。',
  CIRCUIT_BREAKER_COOLDOWN: '数据源熔断冷却时间（秒）。',
  PREFETCH_REALTIME_QUOTES: '分析前预取实时行情数据。',
  // 基本面管线
  ENABLE_FUNDAMENTAL_PIPELINE: '启用基本面数据获取管线。',
  FUNDAMENTAL_STAGE_TIMEOUT_SECONDS: '管线每阶段超时时间（秒）。',
  FUNDAMENTAL_FETCH_TIMEOUT_SECONDS: '单次数据请求超时时间（秒）。',
  FUNDAMENTAL_RETRY_MAX: '数据获取失败时最大重试次数。',
  FUNDAMENTAL_CACHE_TTL_SECONDS: '基本面数据缓存有效期（秒）。',
  FUNDAMENTAL_CACHE_MAX_ENTRIES: '基本面缓存最大条目数。',
  // 组合风控
  PORTFOLIO_RISK_CONCENTRATION_ALERT_PCT: '单一持仓占比超过此阈值时触发预警。',
  PORTFOLIO_RISK_DRAWDOWN_ALERT_PCT: '组合最大回撤超过此阈值时触发预警。',
  PORTFOLIO_RISK_STOP_LOSS_ALERT_PCT: '止损位触发预警的百分比阈值。',
  PORTFOLIO_RISK_STOP_LOSS_NEAR_RATIO: '价格接近止损位时的预警比率。',
  PORTFOLIO_RISK_LOOKBACK_DAYS: '风控回溯计算的天数。',
  PORTFOLIO_FX_UPDATE_ENABLED: '启用港股/美股汇率自动更新。',
  // Agent 扩展
  AGENT_NL_ROUTING: '启用自然语言智能路由匹配策略。',
  AGENT_DEEP_RESEARCH_BUDGET: '深度研究模式的 Token 预算上限。',
  AGENT_DEEP_RESEARCH_TIMEOUT: '深度研究模式的执行超时（秒）。',
  AGENT_EVENT_MONITOR_ENABLED: '启用事件监控，自动检测重大市场事件。',
  AGENT_EVENT_MONITOR_INTERVAL_MINUTES: '事件监控检查间隔（分钟）。',
  AGENT_EVENT_ALERT_RULES_JSON: '事件告警规则 JSON 配置。',
  // 视觉
  VISION_PROVIDER_PRIORITY: '视觉模型供应商优先级，逗号分隔。',
  // Gemini 扩展
  GEMINI_REQUEST_DELAY: 'Gemini API 请求间隔（秒），防限流。',
  GEMINI_MAX_RETRIES: 'Gemini API 最大重试次数。',
  GEMINI_RETRY_DELAY: 'Gemini API 重试间隔（秒）。',
  // 社交情绪
  SOCIAL_SENTIMENT_API_KEY: '社交情绪分析 API 密钥。',
  SOCIAL_SENTIMENT_API_URL: '社交情绪分析 API 地址。',
  // 调度
  SCHEDULE_ENABLED: '是否启用定时任务调度器。',
  SCHEDULE_RUN_IMMEDIATELY: '应用启动时立即执行一次分析。',
  RUN_IMMEDIATELY: '强制立即运行一次分析。',
  MARKET_REVIEW_ENABLED: '启用每日市场复盘功能。',
  MARKET_REVIEW_REGION: '市场复盘区域：cn（A股） / us（美股） / hk（港股）。',
  TRADING_DAY_CHECK_ENABLED: '启用交易日检查，非交易日跳过定时任务。',
  // 系统
  HTTPS_PROXY: 'HTTPS 代理地址，可留空。',
  LOG_DIR: '日志文件存储目录。',
  DEBUG: '启用调试模式，输出详细日志。',
  DATABASE_PATH: 'SQLite 数据库文件路径。',
  CONFIG_VALIDATE_MODE: '配置验证模式：strict / warn / off。',
}

function getFieldTitle(key, fallback) {
  return fieldTitleMap[key] || fallback || key
}
function getFieldDesc(key, fallback) {
  return fieldDescMap[key] || fallback || ''
}

// =============================
// LLM 渠道预设
// =============================
const channelPresets = {
  aihubmix: { label: 'AIHubmix（聚合平台）', protocol: 'openai', baseUrl: 'https://aihubmix.com/v1', placeholder: 'gpt-4o-mini,claude-3-5-sonnet,qwen-plus' },
  deepseek: { label: 'DeepSeek 官方', protocol: 'deepseek', baseUrl: 'https://api.deepseek.com/v1', placeholder: 'deepseek-chat,deepseek-reasoner' },
  dashscope: { label: '通义千问（Dashscope）', protocol: 'openai', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', placeholder: 'qwen-plus,qwen-turbo' },
  zhipu: { label: '智谱 GLM', protocol: 'openai', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', placeholder: 'glm-4-flash,glm-4-plus' },
  moonshot: { label: 'Moonshot（月之暗面）', protocol: 'openai', baseUrl: 'https://api.moonshot.cn/v1', placeholder: 'moonshot-v1-8k' },
  siliconflow: { label: '硅基流动（SiliconFlow）', protocol: 'openai', baseUrl: 'https://api.siliconflow.cn/v1', placeholder: 'Qwen/Qwen3-8B,deepseek-ai/DeepSeek-V3' },
  openrouter: { label: 'OpenRouter', protocol: 'openai', baseUrl: 'https://openrouter.ai/api/v1', placeholder: 'openai/gpt-4o,anthropic/claude-3-5-sonnet' },
  gemini: { label: 'Gemini 官方', protocol: 'gemini', baseUrl: '', placeholder: 'gemini-2.5-flash,gemini-2.5-pro' },
  anthropic: { label: 'Anthropic 官方', protocol: 'anthropic', baseUrl: '', placeholder: 'claude-3-5-sonnet-20241022' },
  openai: { label: 'OpenAI 官方', protocol: 'openai', baseUrl: 'https://api.openai.com/v1', placeholder: 'gpt-4o,gpt-4o-mini' },
  ollama: { label: 'Ollama（本地）', protocol: 'ollama', baseUrl: 'http://127.0.0.1:11434', placeholder: 'llama3.2,qwen2.5' },
  custom: { label: '自定义渠道', protocol: 'openai', baseUrl: '', placeholder: 'model-name-1,model-name-2' },
}
const protocolOptions = [
  { value: 'openai', label: 'OpenAI Compatible' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'vertex_ai', label: 'Vertex AI' },
  { value: 'ollama', label: 'Ollama' },
]

// =============================
// 状态
// =============================
const activeCategory = ref('local')
const dsaServerRunning = ref(false)
const dsaStatus = ref('stopped')
const statusDesc = ref('启动 DSA 后端服务后，可使用股票分析和问股功能')

// 本地设置
const localConfig = reactive({
  workspacePath: '',
  theme: 'dark',
  dataSource: 'binance',
  closeWarning: false,
  maxTabs: 10,
})

// DSA 本地连接配置
const dsaLocal = reactive({
  backendPath: '',
  port: 8100,
})

// DSA 后端配置
const isLoadingDsa = ref(false)
const dsaLoadError = ref('')
const dsaConfigVersion = ref('')
const dsaMaskToken = ref('')
const dsaItems = ref([])         // 原始 items from server
const draftValues = reactive({}) // key -> draft value
const serverValues = reactive({}) // key -> server value
const passwordVisibility = reactive({})
const isSaving = ref(false)

// LLM 渠道
const channels = ref([])
const channelsDirty = ref(false)
const isSavingChannels = ref(false)
const expandedChannels = reactive({})
const addPresetKey = ref('')

// toast
const toast = ref(null)
let toastTimer = null

// 确认对话框
const confirmDialog = reactive({
  show: false,
  title: '',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  onConfirm: () => {},
  onCancel: () => { confirmDialog.show = false },
})

// =============================
// 计算属性
// =============================
const baseUrl = computed(() => `http://127.0.0.1:${dsaLocal.port || 8100}`)

const statusInfo = computed(() => {
  const map = {
    stopped: { color: '#666', text: '未启动', showStart: true, showStop: false },
    starting: { color: '#d29922', text: '正在启动...', showStart: false, showStop: false },
    running: { color: '#2ea043', text: '运行中', showStart: false, showStop: true },
    error: { color: '#da3633', text: '启动失败', showStart: true, showStop: false },
  }
  return map[dsaStatus.value] || map.stopped
})

const DSA_CATEGORIES = ['base', 'ai_model', 'data_source', 'notification', 'system', 'agent', 'backtest', 'uncategorized']
const isDsaCategory = computed(() => DSA_CATEGORIES.includes(activeCategory.value))

// items by category
const itemsByCategory = computed(() => {
  const map = {}
  for (const item of dsaItems.value) {
    const cat = item.schema?.category || 'uncategorized'
    if (!map[cat]) map[cat] = []
    map[cat].push(item)
  }
  return map
})

// ai_model 过滤逻辑（与 DSA SettingsPage 一致）
const AI_MODEL_HIDDEN_KEYS = new Set([
  'LLM_CHANNELS', 'LLM_TEMPERATURE', 'LITELLM_MODEL', 'AGENT_LITELLM_MODEL', 'LITELLM_FALLBACK_MODELS',
  'AIHUBMIX_KEY', 'DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEYS',
  'GEMINI_API_KEY', 'GEMINI_API_KEYS', 'GEMINI_MODEL', 'GEMINI_MODEL_FALLBACK', 'GEMINI_TEMPERATURE',
  'ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEYS', 'ANTHROPIC_MODEL', 'ANTHROPIC_TEMPERATURE', 'ANTHROPIC_MAX_TOKENS',
  'OPENAI_API_KEY', 'OPENAI_API_KEYS', 'OPENAI_BASE_URL', 'OPENAI_MODEL', 'OPENAI_VISION_MODEL', 'OPENAI_TEMPERATURE',
  'VISION_MODEL',
])
const LLM_CHANNEL_KEY_RE = /^LLM_[A-Z0-9]+_(PROTOCOL|BASE_URL|API_KEY|API_KEYS|MODELS|EXTRA_HEADERS|ENABLED)$/

const filteredActiveItems = computed(() => {
  const raw = itemsByCategory.value[activeCategory.value] || []
  if (activeCategory.value === 'ai_model') {
    const rawMap = new Map(raw.map(i => [i.key, String(i.value ?? '')]))
    const hasChannels = Boolean((rawMap.get('LLM_CHANNELS') || '').trim())
    const hasLitellmConfig = Boolean((rawMap.get('LITELLM_CONFIG') || '').trim())
    return raw.filter(item => {
      // 已在 AI 编辑器中手动管理的 key
      if (AI_MODEL_MANAGED_KEYS.has(item.key)) return false
      if (hasChannels && LLM_CHANNEL_KEY_RE.test(item.key)) return false
      if (hasChannels && !hasLitellmConfig && AI_MODEL_HIDDEN_KEYS.has(item.key)) return false
      return true
    })
  }
  return raw
})

// 导航栏分类
const categoryIconMap = {
  local: '⚙️',
  dsa_service: '🔌',
  base: '📋',
  ai_model: '🧠',
  data_source: '📊',
  notification: '🔔',
  system: '🛠️',
  agent: '🤖',
  backtest: '📈',
  uncategorized: '📦',
}

const localCategories = computed(() => [
  { key: 'local', icon: '⚙️', title: '本地设置', description: '工作区、主题与标签页配置。', count: 0 },
  { key: 'dsa_service', icon: '🔌', title: 'DSA 服务', description: '后端服务连接与启停管理。', count: 0 },
])

const dsaCategories = computed(() => {
  if (!dsaServerRunning.value || dsaItems.value.length === 0) {
    return DSA_CATEGORIES.filter(c => c !== 'uncategorized').map(c => ({
      key: c,
      icon: categoryIconMap[c] || '📦',
      title: categoryTitleMap[c] || c,
      description: categoryDescMap[c] || '',
      count: 0,
    }))
  }
  const cats = []
  for (const cat of DSA_CATEGORIES) {
    const items = itemsByCategory.value[cat]
    if (!items || items.length === 0) continue
    cats.push({
      key: cat,
      icon: categoryIconMap[cat] || '📦',
      title: categoryTitleMap[cat] || cat,
      description: categoryDescMap[cat] || '',
      count: items.length,
    })
  }
  return cats
})

const allCategories = computed(() => [
  ...localCategories.value,
  ...dsaCategories.value,
])

const currentCategoryTitle = computed(() => {
  return categoryTitleMap[activeCategory.value] || '当前分类配置项'
})
const currentCategoryDesc = computed(() => {
  return categoryDescMap[activeCategory.value] || '使用统一字段卡片维护当前分类的系统配置。'
})

const hasDirty = computed(() => {
  for (const key of Object.keys(draftValues)) {
    if (normalize(draftValues[key]) !== normalize(serverValues[key])) return true
  }
  return false
})

const dirtyCount = computed(() => {
  let count = 0
  for (const key of Object.keys(draftValues)) {
    if (normalize(draftValues[key]) !== normalize(serverValues[key])) count++
  }
  return count
})

// =============================
// 方法
// =============================
function normalize(v) {
  if (v === null || v === undefined) return ''
  return String(v).trim()
}

function normalizeOptions(opts) {
  if (!opts) return []
  return opts.map(o => {
    if (typeof o === 'string') return { label: o, value: o }
    return o
  })
}

function getDraftValue(key) {
  return key in draftValues ? draftValues[key] : ''
}

function setDraft(key, value) {
  draftValues[key] = value
}

function resetDraft() {
  for (const key of Object.keys(serverValues)) {
    draftValues[key] = serverValues[key]
  }
}

function togglePasswordVisibility(key) {
  passwordVisibility[key] = !passwordVisibility[key]
}

function showToast(type, message) {
  toast.value = { type, message }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = null }, 3200)
}

function showConfirm(title, message, confirmText = '确定', cancelText = '取消') {
  return new Promise((resolve) => {
    confirmDialog.title = title
    confirmDialog.message = message
    confirmDialog.confirmText = confirmText
    confirmDialog.cancelText = cancelText
    confirmDialog.show = true
    confirmDialog.onConfirm = () => { confirmDialog.show = false; resolve(true) }
    confirmDialog.onCancel = () => { confirmDialog.show = false; resolve(false) }
  })
}

// =============================
// 本地设置
// =============================
function saveLocalSetting(key, value) {
  localStorage.setItem(key, String(value))
}

async function browseWorkspace() {
  if (window.electronAPI?.setWorkspacePath) {
    const newPath = await window.electronAPI.setWorkspacePath()
    if (newPath) localConfig.workspacePath = newPath
  }
}

async function onDataSourceChange() {
  const prev = await window.electronAPI?.getDataSource?.() || 'binance'
  if (localConfig.dataSource === prev) return
  const ok = await showConfirm('切换数据源', '切换数据源后，所有已打开的图表页面都会关闭。确定要继续吗？', '确定', '取消')
  if (ok) {
    localStorage.setItem('data-source', localConfig.dataSource)
    window.electronAPI?.setDataSource?.(localConfig.dataSource)
    window.electronAPI?.closeAllChartTabs?.()
  } else {
    localConfig.dataSource = prev
  }
}

// =============================
// DSA 本地连接配置
// =============================
async function loadDsaLocal() {
  if (!window.electronAPI?.getDsaConfig) return
  const cfg = await window.electronAPI.getDsaConfig()
  dsaLocal.backendPath = cfg.backendPath || ''
  dsaLocal.port = cfg.port || 8100
}

async function saveDsaLocal() {
  if (!window.electronAPI?.setDsaConfig) return
  await window.electronAPI.setDsaConfig({
    port: dsaLocal.port,
  })
}

// =============================
// DSA 服务管理
// =============================
async function startServer() {
  await saveDsaLocal()
  dsaStatus.value = 'starting'
  if (window.electronAPI?.startDsaServer) {
    const result = await window.electronAPI.startDsaServer()
    if (result.success) {
      dsaStatus.value = 'running'
      dsaServerRunning.value = true
      statusDesc.value = `服务运行在 ${baseUrl.value}`
      await loadDsaConfig()
    } else {
      dsaStatus.value = 'error'
      statusDesc.value = `启动失败: ${result.error}`
    }
  }
}

async function stopServer() {
  if (window.electronAPI?.stopDsaServer) {
    await window.electronAPI.stopDsaServer()
    dsaStatus.value = 'stopped'
    dsaServerRunning.value = false
    statusDesc.value = '启动 DSA 后端服务后，可使用股票分析和问股功能'
  }
}

function updateStatusFromEvent(data) {
  dsaStatus.value = data.status
  dsaServerRunning.value = data.status === 'running'
  if (data.status === 'running') {
    statusDesc.value = `服务运行在 ${baseUrl.value}`
    if (dsaItems.value.length === 0) loadDsaConfig()
  }
}

// =============================
// DSA 后端配置 API
// =============================

// snake_case -> camelCase
function toCamel(obj) {
  if (Array.isArray(obj)) return obj.map(toCamel)
  if (obj && typeof obj === 'object') {
    const out = {}
    for (const [k, v] of Object.entries(obj)) {
      const ck = k.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
      out[ck] = toCamel(v)
    }
    return out
  }
  return obj
}

// camelCase -> snake_case
function toSnake(obj) {
  if (Array.isArray(obj)) return obj.map(toSnake)
  if (obj && typeof obj === 'object') {
    const out = {}
    for (const [k, v] of Object.entries(obj)) {
      const sk = k.replace(/[A-Z]/g, c => `_${c.toLowerCase()}`)
      out[sk] = toSnake(v)
    }
    return out
  }
  return obj
}

async function loadDsaConfig() {
  if (!dsaServerRunning.value) return
  isLoadingDsa.value = true
  dsaLoadError.value = ''
  try {
    const resp = await fetch(`${baseUrl.value}/api/v1/system/config?include_schema=true`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const raw = await resp.json()
    const data = toCamel(raw)
    dsaConfigVersion.value = data.configVersion || ''
    dsaMaskToken.value = data.maskToken || ''
    dsaItems.value = data.items || []
    // 初始化 draft/server values
    for (const item of dsaItems.value) {
      const val = item.value ?? ''
      serverValues[item.key] = String(val)
      draftValues[item.key] = String(val)
    }
    // 解析 LLM 渠道
    parseChannels()
  } catch (e) {
    dsaLoadError.value = e.message || '未知错误'
  } finally {
    isLoadingDsa.value = false
  }
}

async function saveDsaBackendConfig() {
  if (!hasDirty.value || isSaving.value) return
  isSaving.value = true
  try {
    const items = []
    for (const key of Object.keys(draftValues)) {
      if (normalize(draftValues[key]) !== normalize(serverValues[key])) {
        items.push({ key, value: draftValues[key] })
      }
    }
    const body = toSnake({
      configVersion: dsaConfigVersion.value,
      maskToken: dsaMaskToken.value,
      reloadNow: true,
      items,
    })
    const resp = await fetch(`${baseUrl.value}/api/v1/system/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    showToast('success', '配置已保存')
    // 重新加载
    await loadDsaConfig()
  } catch (e) {
    showToast('error', `保存失败: ${e.message}`)
  } finally {
    isSaving.value = false
  }
}

// =============================
// 配置导入/导出
// =============================
async function exportConfig() {
  if (dsaItems.value.length === 0) return
  // 构建 .env 格式内容
  const lines = []
  lines.push(`# Prophet DSA Config Export`)
  lines.push(`# ${new Date().toISOString()}`)
  lines.push('')
  for (const item of dsaItems.value) {
    const val = getDraftValue(item.key)
    if (item.schema?.isSensitive && val === dsaMaskToken.value) continue
    lines.push(`${item.key}=${val}`)
  }
  const content = lines.join('\n')
  if (window.electronAPI?.exportConfig) {
    const result = await window.electronAPI.exportConfig(content, 'prophet-config.env')
    if (result.success) {
      showToast('success', '配置已导出')
    } else if (result.error) {
      showToast('error', `导出失败: ${result.error}`)
    }
  } else {
    // 浏览器模式降级：下载文件
    const blob = new Blob([content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'prophet-config.env'
    a.click()
    URL.revokeObjectURL(a.href)
    showToast('success', '配置已导出')
  }
}

async function importConfig() {
  let content = ''
  let fileName = ''

  if (window.electronAPI?.importConfig) {
    const result = await window.electronAPI.importConfig()
    if (!result.success) return
    content = result.content
    fileName = result.path
  } else {
    // 浏览器模式降级：使用 file input
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.env,.json'
    const file = await new Promise(resolve => {
      input.onchange = () => resolve(input.files[0])
      input.click()
    })
    if (!file) return
    content = await file.text()
    fileName = file.name
  }

  // 解析 .env 格式
  const items = []
  const existingKeys = new Set(dsaItems.value.map(i => i.key))
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx <= 0) continue
    const key = trimmed.substring(0, eqIdx).trim()
    const val = trimmed.substring(eqIdx + 1).trim()
    if (existingKeys.has(key)) {
      items.push({ key, value: val })
    }
  }

  if (items.length === 0) {
    showToast('error', '未找到可导入的配置项')
    return
  }

  const ok = await showConfirm(
    '导入配置',
    `将从文件导入 ${items.length} 项配置，已有值将被覆盖。确定继续？`,
    '导入',
    '取消'
  )
  if (!ok) return

  // 写入 draft
  for (const { key, value } of items) {
    draftValues[key] = value
  }
  showToast('success', `已导入 ${items.length} 项配置，请点击「保存配置」生效`)
}

// =============================
// LLM 渠道管理
// =============================
function parseChannels() {
  const channelNamesItem = dsaItems.value.find(i => i.key === 'LLM_CHANNELS')
  const channelNames = (channelNamesItem?.value || '').split(',').map(s => s.trim()).filter(Boolean)
  if (channelNames.length === 0) {
    channels.value = []
    return
  }
  const allItems = new Map(dsaItems.value.map(i => [i.key, i.value ?? '']))
  channels.value = channelNames.map(name => {
    const prefix = `LLM_${name.toUpperCase()}`
    const protocol = allItems.get(`${prefix}_PROTOCOL`) || 'openai'
    const baseUrl = allItems.get(`${prefix}_BASE_URL`) || ''
    const apiKey = allItems.get(`${prefix}_API_KEY`) || allItems.get(`${prefix}_API_KEYS`) || ''
    const models = allItems.get(`${prefix}_MODELS`) || ''
    const enabled = allItems.get(`${prefix}_ENABLED`) !== 'false'
    // 尝试匹配预设
    let preset = 'custom'
    for (const [pk, pv] of Object.entries(channelPresets)) {
      if (pk === name || (pv.protocol === protocol && pv.baseUrl && pv.baseUrl === baseUrl)) {
        preset = pk
        break
      }
    }
    return reactive({
      name,
      preset,
      protocol,
      baseUrl,
      apiKey,
      models,
      enabled,
      showKey: false,
      testing: false,
      discovering: false,
      testResult: null,
    })
  })
}

function addChannel() {
  const newIdx = channels.value.length
  channels.value.push(reactive({
    name: '',
    preset: 'custom',
    protocol: 'openai',
    baseUrl: '',
    apiKey: '',
    models: '',
    enabled: true,
    showKey: false,
    testing: false,
    discovering: false,
    testResult: null,
  }))
  expandedChannels[newIdx] = true
  channelsDirty.value = true
}

function addChannelFromPreset() {
  const pk = addPresetKey.value
  if (!pk) return
  const preset = channelPresets[pk]
  if (!preset) return
  const newIdx = channels.value.length
  channels.value.push(reactive({
    name: pk,
    preset: pk,
    protocol: preset.protocol,
    baseUrl: preset.baseUrl,
    apiKey: '',
    models: '',
    enabled: true,
    showKey: false,
    testing: false,
    discovering: false,
    testResult: null,
  }))
  expandedChannels[newIdx] = true
  channelsDirty.value = true
  addPresetKey.value = ''
}

function removeChannel(idx) {
  channels.value.splice(idx, 1)
  // re-index expandedChannels
  const updated = {}
  for (let i = 0; i < channels.value.length; i++) {
    updated[i] = i < idx ? !!expandedChannels[i] : !!expandedChannels[i + 1]
  }
  Object.keys(expandedChannels).forEach(k => delete expandedChannels[k])
  Object.assign(expandedChannels, updated)
  channelsDirty.value = true
}

function onChannelPresetChange(idx) {
  const ch = channels.value[idx]
  const preset = channelPresets[ch.preset]
  if (!preset) return
  ch.protocol = preset.protocol
  ch.baseUrl = preset.baseUrl
  if (!ch.name) ch.name = ch.preset
  channelsDirty.value = true
}

function markChannelsDirty() {
  channelsDirty.value = true
}

function toggleChannelExpand(idx) {
  expandedChannels[idx] = !expandedChannels[idx]
}

function protocolLabel(protocol) {
  const match = protocolOptions.find(p => p.value === protocol)
  return match ? match.label : protocol
}

function channelModelCount(ch) {
  if (!ch.models) return 0
  return ch.models.split(',').filter(m => m.trim()).length
}

function channelStatusClass(ch) {
  if (!ch.apiKey) return 'status-warn'
  if (ch.testResult?.ok) return 'status-ok'
  if (ch.testResult && !ch.testResult.ok) return 'status-error'
  return 'status-idle'
}

const enabledChannelCount = computed(() => channels.value.filter(c => c.enabled).length)

// 备选模型多选辅助
function isFallbackSelected(modelValue) {
  const current = getDraftValue('LITELLM_FALLBACK_MODELS') || ''
  const list = current.split(',').map(m => m.trim()).filter(Boolean)
  return list.includes(modelValue)
}

function toggleFallbackModel(modelValue, checked) {
  const current = getDraftValue('LITELLM_FALLBACK_MODELS') || ''
  const list = current.split(',').map(m => m.trim()).filter(Boolean)
  if (checked) {
    if (!list.includes(modelValue)) list.push(modelValue)
  } else {
    const idx = list.indexOf(modelValue)
    if (idx >= 0) list.splice(idx, 1)
  }
  setDraft('LITELLM_FALLBACK_MODELS', list.join(','))
}

// 运行时参数：在 dsaItems 中查找单个 key
function findDsaItem(key) {
  return (dsaItems.value || []).find(i => i.key === key)
}

const temperatureDisplay = computed(() => {
  const v = getDraftValue('LLM_TEMPERATURE')
  return v !== undefined && v !== '' ? parseFloat(v).toFixed(1) : '0.7'
})

// 从已配置渠道中收集所有可用模型（protocol/model 格式）
const allChannelModels = computed(() => {
  const result = []
  for (const ch of channels.value) {
    if (!ch.models) continue
    const models = ch.models.split(',').map(m => m.trim()).filter(Boolean)
    const protocol = ch.protocol || 'openai'
    for (const model of models) {
      // 如果模型已包含 / 前缀则原样使用，否则加上 protocol/
      const fullName = model.includes('/') ? model : `${protocol}/${model}`
      result.push({ label: `${model}  (${ch.name})`, value: fullName })
    }
  }
  return result
})

// 这些 key 已在 AI 模型编辑器中手动管理，不再显示在通用字段列表中
const AI_MODEL_MANAGED_KEYS = new Set([
  'LITELLM_MODEL', 'AGENT_LITELLM_MODEL', 'LITELLM_FALLBACK_MODELS',
  'VISION_MODEL', 'LLM_TEMPERATURE', 'LITELLM_CONFIG',
])

async function saveChannels() {
  isSavingChannels.value = true
  try {
    const items = []
    const names = channels.value.map(c => c.name).filter(Boolean)
    items.push({ key: 'LLM_CHANNELS', value: names.join(',') })
    for (const ch of channels.value) {
      if (!ch.name) continue
      const prefix = `LLM_${ch.name.toUpperCase()}`
      items.push({ key: `${prefix}_PROTOCOL`, value: ch.protocol })
      items.push({ key: `${prefix}_BASE_URL`, value: ch.baseUrl })
      items.push({ key: `${prefix}_API_KEY`, value: ch.apiKey })
      items.push({ key: `${prefix}_MODELS`, value: ch.models })
      items.push({ key: `${prefix}_ENABLED`, value: ch.enabled ? 'true' : 'false' })
    }
    const body = toSnake({
      configVersion: dsaConfigVersion.value,
      maskToken: dsaMaskToken.value,
      reloadNow: true,
      items,
    })
    const resp = await fetch(`${baseUrl.value}/api/v1/system/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${resp.status}`)
    }
    showToast('success', '渠道配置已保存')
    channelsDirty.value = false
    await loadDsaConfig()
  } catch (e) {
    showToast('error', `保存失败: ${e.message}`)
  } finally {
    isSavingChannels.value = false
  }
}

async function testChannel(idx) {
  const ch = channels.value[idx]
  ch.testing = true
  ch.testResult = null
  try {
    const resp = await fetch(`${baseUrl.value}/api/v1/system/config/llm/test-channel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: ch.name,
        protocol: ch.protocol,
        base_url: ch.baseUrl,
        api_key: ch.apiKey,
        models: ch.models ? ch.models.split(',').map(m => m.trim()).filter(Boolean) : [],
        enabled: ch.enabled,
      }),
    })
    const data = toCamel(await resp.json())
    ch.testResult = {
      ok: data.success ?? resp.ok,
      message: data.message || (resp.ok ? '连接成功' : '连接失败'),
    }
  } catch (e) {
    ch.testResult = { ok: false, message: e.message || '请求失败' }
  } finally {
    ch.testing = false
  }
}

async function discoverModels(idx) {
  const ch = channels.value[idx]
  ch.discovering = true
  ch.testResult = null
  try {
    const resp = await fetch(`${baseUrl.value}/api/v1/system/config/llm/discover-models`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: ch.name,
        protocol: ch.protocol,
        base_url: ch.baseUrl,
        api_key: ch.apiKey,
      }),
    })
    const data = toCamel(await resp.json())
    if (data.models && data.models.length > 0) {
      ch.models = data.models.join(',')
      channelsDirty.value = true
      ch.testResult = { ok: true, message: `发现 ${data.models.length} 个模型` }
    } else {
      ch.testResult = { ok: false, message: data.message || '未发现模型' }
    }
  } catch (e) {
    ch.testResult = { ok: false, message: e.message || '请求失败' }
  } finally {
    ch.discovering = false
  }
}

// =============================
// 初始化
// =============================
onMounted(async () => {
  // 加载本地设置
  localConfig.theme = localStorage.getItem('theme') || 'dark'
  localConfig.closeWarning = localStorage.getItem('close-warning') === 'true'
  localConfig.maxTabs = parseInt(localStorage.getItem('max-tabs') || '10', 10)

  if (window.electronAPI?.getWorkspacePath) {
    localConfig.workspacePath = await window.electronAPI.getWorkspacePath() || ''
  }
  if (window.electronAPI?.getDataSource) {
    localConfig.dataSource = await window.electronAPI.getDataSource() || 'binance'
  }

  // 加载 DSA 本地配置
  await loadDsaLocal()

  // 加载 DSA 服务状态
  if (window.electronAPI?.getDsaStatus) {
    const info = await window.electronAPI.getDsaStatus()
    dsaStatus.value = info.status
    dsaServerRunning.value = info.status === 'running'
    if (info.status === 'running') {
      statusDesc.value = `服务运行在 ${baseUrl.value}`
    }
  }

  // 监听状态变化
  if (window.electronAPI?.onDsaStatusChanged) {
    window.electronAPI.onDsaStatusChanged(updateStatusFromEvent)
  }

  // 如果服务已在运行，加载后端配置
  if (dsaServerRunning.value) {
    await loadDsaConfig()
  }
})

onUnmounted(() => {
  clearTimeout(toastTimer)
})

// 当切换到 DSA 分类且数据未加载时自动加载
watch(activeCategory, (cat) => {
  if (DSA_CATEGORIES.includes(cat) && dsaServerRunning.value && dsaItems.value.length === 0) {
    loadDsaConfig()
  }
})
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.settings-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  color: #ccc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  overflow: hidden;
}

/* 顶部 */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}
.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}
.header-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #888;
}
.header-actions {
  display: flex;
  gap: 8px;
}

/* Toast */
.toast-bar {
  padding: 8px 24px;
  flex-shrink: 0;
}
.toast {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
}
.toast.success {
  background: rgba(46, 160, 67, 0.15);
  color: #2ea043;
  border: 1px solid rgba(46, 160, 67, 0.3);
}
.toast.error {
  background: rgba(218, 54, 51, 0.15);
  color: #da3633;
  border: 1px solid rgba(218, 54, 51, 0.3);
}

/* 主体 */
.settings-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧导航 */
.category-nav {
  width: 240px;
  min-width: 240px;
  border-right: 1px solid #333;
  overflow-y: auto;
  padding: 8px 0;
  flex-shrink: 0;
}
.nav-group-label {
  padding: 12px 16px 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: #666;
  letter-spacing: 0.5px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  position: relative;
  transition: background 0.15s;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.nav-item.active {
  background: rgba(74, 158, 255, 0.08);
  border-left-color: #4a9eff;
}
.nav-icon {
  font-size: 16px;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}
.nav-text {
  flex: 1;
  min-width: 0;
}
.nav-title {
  font-size: 13px;
  font-weight: 500;
  color: #ddd;
}
.nav-item.active .nav-title {
  color: #4a9eff;
}
.nav-desc {
  font-size: 11px;
  color: #666;
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.nav-badge {
  position: absolute;
  top: 10px;
  right: 12px;
  background: rgba(255, 255, 255, 0.1);
  color: #aaa;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
}

/* 右侧内容 */
.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

/* 卡片 */
.section-card {
  background: #252526;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}
.section-desc {
  font-size: 12px;
  color: #888;
  margin-bottom: 20px;
}

/* 字段 */
.field-item {
  margin-bottom: 20px;
}
.field-item:last-child {
  margin-bottom: 0;
}
.field-item > label,
.field-label-row > label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
}
.field-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.field-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.flex-1 {
  flex: 1;
}
.field-input {
  width: 100%;
  padding: 7px 12px;
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.field-input:focus {
  border-color: #4a9eff;
}
.field-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.field-textarea {
  min-height: 72px;
  resize: vertical;
}
.field-desc {
  font-size: 11px;
  color: #666;
  margin-top: 4px;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.checkbox-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* badge */
.badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}
.badge.sensitive {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}
.badge.readonly {
  background: rgba(150, 150, 150, 0.15);
  color: #999;
}

/* 按钮 */
.btn {
  padding: 7px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #0e639c;
  color: #fff;
  border-color: #0e639c;
}
.btn-primary:hover:not(:disabled) {
  background: #1177bb;
}
.btn-secondary {
  background: #2d2d2d;
  color: #ccc;
  border-color: #444;
}
.btn-secondary:hover:not(:disabled) {
  background: #3a3a3a;
}
.btn-browse {
  background: #2d2d2d;
  color: #ccc;
  border-color: #444;
  padding: 7px 12px;
}
.btn-browse:hover {
  background: #3a3a3a;
}
.btn-start {
  background: #2ea043;
  color: #fff;
  border-color: #2ea043;
}
.btn-start:hover {
  background: #3ab554;
}
.btn-stop {
  background: #da3633;
  color: #fff;
  border-color: #da3633;
}
.btn-stop:hover {
  background: #e74c3c;
}
.btn-icon {
  padding: 4px 8px;
  font-size: 14px;
  line-height: 1;
}
.btn-danger-icon {
  background: transparent;
  color: #da3633;
  border-color: transparent;
}
.btn-danger-icon:hover {
  background: rgba(218, 54, 51, 0.15);
}

/* 状态行 */
.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-text {
  font-size: 14px;
  color: #ccc;
}

/* 渠道编辑器 */
.llm-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.llm-group {
  background: #252526;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  padding: 14px;
}
.llm-group-title {
  font-size: 14px;
  font-weight: 600;
  color: #ddd;
  margin-bottom: 10px;
}
.channel-add-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.channel-add-select {
  width: 200px;
}
.channel-count-badge {
  margin-left: auto;
  font-size: 12px;
  color: #888;
  background: #333;
  padding: 2px 8px;
  border-radius: 10px;
}
.channel-empty-hint {
  font-size: 13px;
  color: #666;
  padding: 8px 0;
}
.channels-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.channel-card {
  background: #1e1e1e;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.channel-card.expanded {
  border-color: #4a9eff;
}
.channel-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.channel-row:hover {
  background: #2a2a2a;
}
.channel-expand-arrow {
  font-size: 10px;
  color: #666;
  transition: transform 0.2s;
  display: inline-block;
  width: 14px;
  flex-shrink: 0;
}
.channel-expand-arrow.open {
  transform: rotate(90deg);
}
.channel-enable-check {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.channel-enable-check input[type="checkbox"] {
  margin: 0;
}
.channel-row-name {
  font-size: 13px;
  color: #ddd;
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.channel-row-badge {
  font-size: 11px;
  color: #999;
  background: #333;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.channel-row-models {
  font-size: 11px;
  color: #777;
  flex-shrink: 0;
}
.channel-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.channel-status-dot.status-ok { background: #2ea043; }
.channel-status-dot.status-error { background: #da3633; }
.channel-status-dot.status-warn { background: #d29922; }
.channel-status-dot.status-idle { background: #555; }
.channel-row-warn {
  font-size: 11px;
  color: #d29922;
  flex-shrink: 0;
}
.channel-row-delete {
  margin-left: auto;
  flex-shrink: 0;
}
.channel-body {
  padding: 12px;
  border-top: 1px solid #3a3a3a;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.channel-field label {
  display: block;
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}
.channel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}
.test-result {
  font-size: 12px;
}
.test-result.success {
  color: #2ea043;
}
.test-result.error {
  color: #da3633;
}
.channel-save-row {
  margin-top: 4px;
}
/* 运行时参数 */
.runtime-params-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.temperature-field {
  margin-top: 12px;
}
.temperature-value {
  font-size: 13px;
  color: #4a9eff;
  font-weight: 600;
  margin-left: auto;
}
.temperature-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #2ea043, #d29922, #da3633);
  outline: none;
  margin: 8px 0 4px;
}
.temperature-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #4a9eff;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}
.temperature-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #4a9eff;
  cursor: pointer;
}
.temperature-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #666;
}
/* 备选模型多选 */
.fallback-model-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 140px;
  overflow-y: auto;
  padding: 6px 8px;
  background: #1e1e1e;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
}
.fallback-model-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #ccc;
  cursor: pointer;
  padding: 2px 0;
}
.fallback-model-option input[type="checkbox"] {
  margin: 0;
}
.fallback-model-option:hover {
  color: #fff;
}

/* 空状态 / 加载 / 错误 */
.empty-state,
.loading-state,
.error-state {
  text-align: center;
  padding: 60px 20px;
  color: #888;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.empty-title,
.error-title {
  font-size: 16px;
  font-weight: 500;
  color: #ccc;
  margin-bottom: 8px;
}
.empty-desc,
.error-desc {
  font-size: 13px;
  color: #666;
  margin-bottom: 16px;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #333;
  border-top-color: #4a9eff;
  border-radius: 50%;
  margin: 0 auto 12px;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}
.dialog-box {
  background: #2e2c29;
  border: 1px solid #444;
  border-radius: 8px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}
.dialog-box h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: #fff;
}
.dialog-box p {
  margin: 0 0 20px;
  font-size: 14px;
  color: #ccc;
  line-height: 1.5;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
