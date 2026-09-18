/**
 * Home Assistant - Consumable Tracking Card (耗材与事务跟踪卡片)
 * Version: 1.1.2 [Theme-A: Tech Blue]
 */
console.info(
  '%c CONSUMABLE-TRACKING-CARD %c v1.1.2 [科技蔚蓝] %c',
  'background:#0284c7;color:#fff;padding:3px 6px;border-radius:3px 0 0 3px;font-weight:bold;font-size:11px;',
  'background:#38bdf8;color:#0f172a;padding:3px 6px;border-radius:0 3px 3px 0;font-weight:bold;font-size:11px;',
  'background:transparent;'
);
/**
 * Consumable Tracking Card (耗材与事务跟踪卡片)
 * 紧凑、现代、简约风格，原生支持 Home Assistant
 */

class ConsumableTrackingCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._items = [];
    this._filterCategory = 'all';
    this._showModal = false;
    this._editItem = null;
    this._showResetModal = false;
    this._resetTargetItem = null;
    this._showHistoryModal = false;
    this._historyTargetItem = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this._fetchItems();
      this._subscribeEvents();
    }
  }

  setConfig(config) {
    this._config = {
      title: config.title || '耗材与事务跟踪',
      show_add: config.show_add !== false,
      filter_category: config.filter_category || null,
      ...config
    };
    this._render();
  }

  getCardSize() {
    return Math.max(2, Math.ceil((this._items.length || 1) * 1.5));
  }

  static getStubConfig() {
    return {
      title: '耗材与事务跟踪',
      show_add: true
    };
  }

  async _fetchItems() {
    if (!this._hass) return;
    try {
      const items = await this._hass.callWS({
        type: 'consumable_tracking/list_items'
      });
      this._items = Array.isArray(items) ? items : [];
      this._render();
    } catch (err) {
      // 兼容直接从 sensor.* 实体读取模式
      this._fallbackFromSensors();
    }
  }

  _fallbackFromSensors() {
    if (!this._hass || !this._hass.states) return;
    const items = [];
    Object.keys(this._hass.states).forEach(entityId => {
      if (entityId.startsWith('sensor.consumable_')) {
        const stateObj = this._hass.states[entityId];
        const attrs = stateObj.attributes || {};
        items.push({
          id: attrs.item_id || entityId.replace('sensor.consumable_', ''),
          name: attrs.friendly_name || attrs.name || entityId,
          category: attrs.category || '通用',
          icon: attrs.icon || 'mdi:package-variant',
          start_date: attrs.start_date,
          start_ym: attrs.start_ym,
          expected_end_date: attrs.expected_end_date,
          expected_ym: attrs.expected_ym,
          duration_value: attrs.duration_value || 12,
          duration_unit: attrs.duration_unit || 'month',
          remaining_days: Number(stateObj.state) || 0,
          progress: attrs.progress || 0,
          status: attrs.status || 'good',
          note: attrs.note || '',
          history: attrs.history || []
        });
      }
    });
    items.sort((a, b) => a.remaining_days - b.remaining_days);
    this._items = items;
    this._render();
  }

  _subscribeEvents() {
    if (this._hass && this._hass.connection) {
      this._hass.connection.subscribeEvents(() => {
        this._fetchItems();
      }, 'consumable_tracking_updated');
    }
  }

  // 获取所有分类
  _getCategories() {
    const cats = new Set();
    this._items.forEach(it => {
      if (it.category) cats.add(it.category);
    });
    return Array.from(cats);
  }

  // 格式化当前年月选择 (YYYY-MM)
  _getTodayYM() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  _render() {
    if (!this.shadowRoot) return;

    let displayItems = this._items;
    if (this._filterCategory && this._filterCategory !== 'all') {
      displayItems = displayItems.filter(i => i.category === this._filterCategory);
    }

    const categories = this._getCategories();

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --ct-card-bg: var(--ha-card-background, var(--card-background-color, #ffffff));
          --ct-text-primary: var(--primary-text-color, #1f2937);
          --ct-text-secondary: var(--secondary-text-color, #6b7280);
          --ct-accent-green: #10B981;
          --ct-accent-amber: #F59E0B;
          --ct-accent-red: #EF4444;
          --ct-border-color: var(--divider-color, rgba(0, 0, 0, 0.08));
          --ct-track-bg: var(--secondary-background-color, #f3f4f6);
        }

        ha-card {
          padding: 16px;
          border-radius: 12px;
          background: var(--ct-card-bg);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.05));
          position: relative;
        }

        /* 标题与顶部工具条 */
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .card-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--ct-text-primary);
          margin: 0;
        }
        .item-count-badge {
          font-size: 11px;
          padding: 2px 6px;
          background: var(--ct-track-bg);
          color: var(--ct-text-secondary);
          border-radius: 10px;
        }

        .btn-add {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: var(--primary-color, #0284c7);
          color: #fff;
          border: none;
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 500;
          border-radius: 6px;
          cursor: pointer;
          transition: opacity 0.2s;
        }
        .btn-add:hover {
          opacity: 0.9;
        }
        .header-actions-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .btn-notify-test {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 30px;
          height: 30px;
          background: var(--secondary-background-color, #f3f4f6);
          color: var(--secondary-text-color, #4b5563);
          border: 1px solid var(--divider-color, #e5e7eb);
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
          box-sizing: border-box;
        }
        .btn-notify-test ha-icon {
          --mdc-icon-size: 16px;
        }
        .btn-notify-test:hover {
          background: var(--primary-color, #0097a7);
          color: #ffffff;
          border-color: var(--primary-color, #0097a7);
          transform: translateY(-1px);
        }
        .btn-notify-test.loading {
          opacity: 0.5;
          pointer-events: none;
        }
        .item-card {
          transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
        }
        .item-card.dragging {
          opacity: 0.45;
          transform: scale(0.98);
          border: 2px dashed var(--primary-color, #0097a7);
        }
        .item-card.drag-over-top {
          border-top: 3px solid var(--primary-color, #0097a7) !important;
        }
        .item-card.drag-over-bottom {
          border-bottom: 3px solid var(--primary-color, #0097a7) !important;
        }
        .drag-handle {
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--disabled-text-color, #9ca3af);
          cursor: grab;
          padding: 2px;
          margin-right: 2px;
          border-radius: 4px;
          transition: color 0.15s;
        }
        .drag-handle ha-icon {
          --mdc-icon-size: 18px;
        }
        .drag-handle:hover {
          color: var(--primary-color, #0097a7);
          background: rgba(0, 0, 0, 0.04);
        }
        .drag-handle:active {
          cursor: grabbing;
        }

        /* 分类筛选 Chip */
        .category-chips {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          margin-bottom: 12px;
          padding-bottom: 4px;
        }
        .chip {
          font-size: 11px;
          padding: 3px 8px;
          border-radius: 12px;
          background: var(--ct-track-bg);
          color: var(--ct-text-secondary);
          cursor: pointer;
          white-space: nowrap;
          border: 1px solid transparent;
          transition: all 0.2s;
        }
        .chip.active {
          background: var(--primary-color, #0284c7);
          color: #fff;
          font-weight: 500;
        }

        /* 耗材卡片列表 */
        .item-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .item-card {
          background: var(--ct-card-bg, #ffffff);
          border: 1px solid var(--ct-border-color, #e5e7eb);
          border-radius: 12px;
          padding: 12px 14px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.03);
          transition: transform 0.15s, box-shadow 0.15s;
        }
        .item-card:hover {
          box-shadow: 0 3px 10px rgba(0,0,0,0.07);
        }

        /* 顶部信息与操作行（对齐附图） */
        .item-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          gap: 8px;
        }
        .item-info {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
          flex: 1;
        }
        .drag-handle {
          cursor: grab;
          color: #9ca3af;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2px;
          border-radius: 4px;
          transition: color 0.2s, background 0.2s;
        }
        .drag-handle:hover {
          color: var(--primary-color, #0284c7);
          background: rgba(0,0,0,0.04);
        }
        .drag-handle svg {
          display: block;
        }
        .item-icon {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          background: #f1f5f9;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #0284c7;
          flex-shrink: 0;
        }
        .item-icon ha-icon {
          --mdc-icon-size: 20px;
        }
        .item-title-group {
          display: flex;
          flex-direction: column;
          gap: 3px;
          min-width: 0;
        }
        .item-name {
          font-size: 15px;
          font-weight: 600;
          color: var(--ct-text-primary, #111827);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          line-height: 1.25;
        }
        .item-badge-row {
          display: flex;
          gap: 6px;
          align-items: center;
        }
        .category-tag {
          font-size: 11px;
          color: #64748b;
          background: #f1f5f9;
          padding: 1px 8px;
          border-radius: 10px;
          line-height: 1.3;
          width: fit-content;
        }
        .note-tag {
          font-size: 11px;
          color: #94a3b8;
          max-width: 130px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        /* 顶部右侧操作栏（附图样式） */
        .item-actions {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
        }
        .btn-history {
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          color: #475569;
          font-size: 12px;
          font-weight: 500;
          padding: 4px 10px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s;
          line-height: 1.2;
        }
        .btn-history:hover {
          background: #f1f5f9;
          border-color: #94a3b8;
          color: #1e293b;
        }
        .btn-replace {
          background: #0284c7;
          border: 1px solid #0284c7;
          color: #ffffff;
          font-size: 12px;
          font-weight: 600;
          padding: 4px 10px;
          border-radius: 6px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          transition: all 0.15s;
          line-height: 1.2;
          box-shadow: 0 1px 2px rgba(2, 132, 199, 0.2);
        }
        .btn-replace:hover {
          background: #0369a1;
          border-color: #0369a1;
        }
        .btn-replace svg {
          display: block;
        }
        .btn-icon {
          width: 28px;
          height: 28px;
          padding: 0;
          border: none;
          background: transparent;
          border-radius: 6px;
          cursor: pointer;
          color: #6b7280;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          transition: all 0.15s;
        }
        .btn-icon:hover {
          background: #f3f4f6;
          color: #1f2937;
        }
        .btn-icon.btn-delete:hover {
          color: #ef4444;
          background: #fee2e2;
        }
        .btn-icon ha-icon {
          --mdc-icon-size: 18px;
        }

        /* 进度条与浮动文字（方案 A 科技蔚蓝纯白字·透明底） */
        .progress-section {
          margin-top: 6px;
        }
        .progress-track-wrapper {
          position: relative;
          width: 100%;
          height: 28px;
          background: #cbd5e1;
          border-radius: 14px;
          overflow: hidden;
          display: flex;
          align-items: center;
          container-type: inline-size;
        }
        .progress-fill-mask {
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          border-radius: 14px;
          overflow: hidden;
          transition: width 0.35s ease;
          pointer-events: none;
        }
        .progress-fill-bar {
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 100cqi;
          min-width: 100%;
          border-radius: 14px;
        }
        .progress-fill-bar.status-good {
          background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%) !important;
        }
        .progress-fill-bar.status-warning {
          background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%) !important;
        }
        .progress-fill-bar.status-expired {
          background: linear-gradient(90deg, #e11d48 0%, #fb7185 100%) !important;
        }

        .progress-inner-text {
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          bottom: 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0 12px;
          pointer-events: none;
          z-index: 2;
          white-space: nowrap;
          color: #ffffff !important;
        }
        .progress-inner-text .text-start,
        .progress-inner-text .text-end {
          font-size: 12px;
          font-weight: 600;
          color: #ffffff !important;
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
        }
        .progress-inner-text .text-center {
          font-size: 13px;
          font-weight: 700;
          color: #ffffff !important;
          letter-spacing: 0.2px;
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
        }
        .progress-inner-text .text-center.expired {
          color: #ffffff !important;
          text-shadow: 0 1px 3px rgba(0, 0, 0, 0.6) !important;
        }

        /* 空状态 */
        .empty-state {
          text-align: center;
          padding: 24px;
          color: var(--ct-text-secondary);
          font-size: 13px;
        }

        /* 模态弹窗 */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.45);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 999;
          backdrop-filter: blur(2px);
        }
        .modal-box {
          background: var(--ct-card-bg);
          border-radius: 12px;
          width: 90%;
          max-width: 440px;
          padding: 18px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.2);
          box-sizing: border-box;
        }
        .modal-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--ct-text-primary);
          margin-bottom: 12px;
        }
        .form-group {
          margin-bottom: 12px;
        }
        .form-label {
          display: block;
          font-size: 12px;
          font-weight: 500;
          color: var(--ct-text-primary);
          margin-bottom: 4px;
        }
        .form-input, .form-select {
          width: 100%;
          box-sizing: border-box;
          padding: 8px 10px;
          border-radius: 6px;
          border: 1px solid var(--ct-border-color);
          background: var(--ct-track-bg);
          color: var(--ct-text-primary);
          font-size: 13px;
          outline: none;
        }
        .form-row {
          display: flex;
          gap: 8px;
        }
        .form-row .form-group {
          flex: 1;
        }
        .presets-row {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 4px;
        }
        .preset-btn {
          background: var(--ct-track-bg);
          border: 1px solid var(--ct-border-color);
          color: var(--ct-text-secondary);
          font-size: 11px;
          padding: 2px 6px;
          border-radius: 4px;
          cursor: pointer;
        }
        .preset-btn:hover {
          border-color: var(--primary-color, #0284c7);
          color: var(--primary-color, #0284c7);
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 16px;
        }
        .btn-cancel {
          background: transparent;
          border: 1px solid var(--ct-border-color);
          color: var(--ct-text-secondary);
          padding: 6px 14px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .btn-save {
          background: var(--primary-color, #0284c7);
          color: #fff;
          border: none;
          padding: 6px 16px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
        }
      </style>

      <ha-card>
        <!-- Header -->
        <div class="header">
          <div class="header-left">
            <h2 class="card-title">${this._config.title === '家庭耗材与事务跟踪' ? '耗材与事务跟踪' : (this._config.title || '耗材与事务跟踪')}</h2>
          </div>
          <div class="header-actions-group">
            <button class="btn-notify-test" id="testNotifyBtn" title="发送全量耗材总览通知到企业微信 (测试)">
              <ha-icon icon="mdi:bell-ring-outline"></ha-icon>
            </button>
            ${this._config.show_add ? `
              <button class="btn-add" id="openAddBtn">
                + 新建
              </button>
            ` : ''}
          </div>
        </div>

        <!-- 分类 Chip 过滤 (当分类 > 1 时显示) -->
        ${categories.length > 1 ? `
          <div class="category-chips">
            <span class="chip ${this._filterCategory === 'all' ? 'active' : ''}" data-cat="all">全部</span>
            ${categories.map(c => `
              <span class="chip ${this._filterCategory === c ? 'active' : ''}" data-cat="${c}">${c}</span>
            `).join('')}
          </div>
        ` : ''}

        <!-- 耗材列表 -->
        <div class="item-list">
          ${displayItems.length === 0 ? `
            <div class="empty-state">
              暂无跟踪耗材，点击右上角【新建耗材】开始添加！
            </div>
          ` : displayItems.map(item => this._renderItemCard(item)).join('')}
        </div>

        <!-- 弹窗：新建 / 编辑耗材 -->
        ${this._showModal ? this._renderEditModal() : ''}

        <!-- 弹窗：确认更换并归档 -->
        ${this._showResetModal ? this._renderResetModal() : ''}

        <!-- 弹窗：查看更换历史 -->
        ${this._showHistoryModal ? this._renderHistoryModal() : ''}
      </ha-card>
    `;

    this._bindEvents();
  }

  _resolveIcon(icon) {
    if (!icon || icon === 'mdi:water-filter') {
      return 'mdi:filter';
    }
    return icon;
  }

  _formatYM(dateStr) {
    if (!dateStr) return '-';
    return String(dateStr).slice(0, 7).replace(/-/g, '/');
  }

  _getCenterProgressText(item) {
    if (item.remaining_days < 0) {
      return `已超期 ${Math.abs(item.remaining_days)} 天(0%)`;
    } else if (item.remaining_days === 0) {
      return `今日到期(100%)`;
    }
    return `剩余 ${item.remaining_days} 天(${item.progress}%)`;
  }

  _renderItemCard(item) {
    const statusClass = item.status === 'expired' ? 'status-expired' : (item.status === 'warning' ? 'status-warning' : 'status-good');

    return `
      <div class="item-card" data-id="${item.id}" draggable="true">
        <!-- 顶部信息与操作行（对齐附图） -->
        <div class="item-header">
          <div class="item-info">
            <div class="drag-handle" title="按住拖拽排序">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="8" cy="5" r="1.8"/>
                <circle cx="16" cy="5" r="1.8"/>
                <circle cx="8" cy="12" r="1.8"/>
                <circle cx="16" cy="12" r="1.8"/>
                <circle cx="8" cy="19" r="1.8"/>
                <circle cx="16" cy="19" r="1.8"/>
              </svg>
            </div>
            <div class="item-title-group">
              <span class="item-name" title="${item.name}">${item.name}</span>
            </div>
          </div>

          <div class="item-actions">
            <button type="button" class="btn-history" data-action="history" data-id="${item.id}" title="查看更换历史">历史</button>
            <button type="button" class="btn-replace" data-action="reset" data-id="${item.id}" title="完成并记录更换">已更换</button>
            <button type="button" class="btn-icon" data-action="edit" data-id="${item.id}" title="编辑">
              <ha-icon icon="mdi:pencil-outline"></ha-icon>
            </button>
            <button type="button" class="btn-icon btn-delete" data-action="delete" data-id="${item.id}" title="删除">
              <ha-icon icon="mdi:trash-can-outline"></ha-icon>
            </button>
          </div>
        </div>

        <!-- 底部紧凑横向胶囊进度条（对齐附图） -->
        <div class="progress-section">
          <div class="progress-track-wrapper">
            <div class="progress-fill-mask" style="width: ${Math.min(Math.max(item.progress, 0), 100)}%;">
              <div class="progress-fill-bar ${statusClass}"></div>
            </div>
            <div class="progress-inner-text">
              <span class="text-start">${this._formatYM(item.start_ym || item.start_date)}</span>
              <span class="text-center ${item.status === 'expired' ? 'expired' : ''}">${this._getCenterProgressText(item)}</span>
              <span class="text-end">${this._formatYM(item.expected_ym || item.expected_end_date)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderEditModal() {
    const isEdit = !!this._editItem;
    const item = this._editItem || {
      name: '',
      category: '滤芯',
      icon: 'mdi:filter',
      start_date: this._getTodayYM(),
      duration_value: 12,
      duration_unit: 'month',
      note: ''
    };

    return `
      <div class="modal-overlay" id="modalOverlay">
        <div class="modal-box" id="modalBox">
          <div class="modal-title">${isEdit ? '编辑耗材' : '新建耗材或事务'}</div>

          <!-- 常用快捷模板 -->
          ${!isEdit ? `
            <div class="form-group">
              <label class="form-label">常用预设模板：</label>
              <div class="presets-row">
                <button type="button" class="preset-btn" data-tpl="water_filter">净水器滤芯 (12月)</button>
                <button type="button" class="preset-btn" data-tpl="air_filter">新风滤网 (6月)</button>
                <button type="button" class="preset-btn" data-tpl="sweeper">扫地机边刷/尘盒 (3月)</button>
                <button type="button" class="preset-btn" data-tpl="battery">无线开关/门锁电池 (12月)</button>
                <button type="button" class="preset-btn" data-tpl="sewer">疏浚下水道 (6月)</button>
              </div>
            </div>
          ` : ''}

          <div class="form-group">
            <label class="form-label">耗材/事务名称 *</label>
            <input type="text" class="form-input" id="inp_name" value="${item.name || ''}" placeholder="如：净水器RO滤芯、门锁电池">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">分类</label>
              <input type="text" class="form-input" id="inp_category" value="${item.category || '滤芯'}" placeholder="滤芯 / 电池 / 维护">
            </div>
            <div class="form-group">
              <label class="form-label">MDI 图标</label>
              <input type="text" class="form-input" id="inp_icon" value="${item.icon || 'mdi:package-variant'}" placeholder="mdi:filter">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">开始年月/日期</label>
              <input type="month" class="form-input" id="inp_start_date" value="${(item.start_date || this._getTodayYM()).slice(0, 7)}">
            </div>
            <div class="form-group">
              <label class="form-label">预设周期 (数值)</label>
              <input type="number" class="form-input" id="inp_duration_val" min="1" max="120" value="${item.duration_value || 12}">
            </div>
            <div class="form-group">
              <label class="form-label">单位</label>
              <select class="form-select" id="inp_duration_unit">
                <option value="month" ${item.duration_unit === 'month' ? 'selected' : ''}>个月</option>
                <option value="day" ${item.duration_unit === 'day' ? 'selected' : ''}>天</option>
                <option value="year" ${item.duration_unit === 'year' ? 'selected' : ''}>年</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">规格 / 备忘说明</label>
            <input type="text" class="form-input" id="inp_note" value="${item.note || ''}" placeholder="如：CR2032两粒、400G大通量规格">
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-cancel" id="modalCancelBtn">取消</button>
            <button type="button" class="btn-save" id="modalSaveBtn">保存</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderResetModal() {
    const item = this._resetTargetItem;
    if (!item) return '';

    return `
      <div class="modal-overlay" id="resetModalOverlay">
        <div class="modal-box">
          <div class="modal-title">🔄 确认耗材已更换？</div>
          <p style="font-size:13px;color:var(--ct-text-secondary);margin-bottom:12px;">
            将当前 <strong>${item.name}</strong> 自动归档至历史记录，并以当前日期开启全新的使用周期。
          </p>

          <div class="form-group">
            <label class="form-label">新周期开始年月</label>
            <input type="month" class="form-input" id="reset_start_ym" value="${this._getTodayYM()}">
          </div>

          <div class="form-group">
            <label class="form-label">本次更换备注 (可选)</label>
            <input type="text" class="form-input" id="reset_note" placeholder="如：换成了某品牌加强版">
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-cancel" id="resetCancelBtn">取消</button>
            <button type="button" class="btn-save" id="resetConfirmBtn">确认更换</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderHistoryModal() {
    const item = this._historyTargetItem;
    if (!item) return '';

    const historyList = item.history || [];

    return `
      <div class="modal-overlay" id="historyModalOverlay">
        <div class="modal-box" style="max-width: 440px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--ct-border-color); padding-bottom: 10px;">
            <div class="modal-title" style="margin-bottom: 0;">📜 ${item.name} · 更换历史</div>
            <button type="button" class="btn-icon" id="closeHistoryIconBtn" title="关闭" style="color: var(--ct-text-secondary);">
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </div>

          <div style="max-height: 320px; overflow-y: auto; margin-bottom: 16px; padding-right: 2px;">
            ${historyList.length === 0 ? `
              <div style="text-align: center; padding: 30px 12px; color: var(--ct-text-secondary); font-size: 13px;">
                暂无过往更换记录。<br>耗材使用完毕并在卡片点击【已更换】后，每次使用周期将自动归档在此。
              </div>
            ` : `
              <div style="display: flex; flex-direction: column; gap: 8px;">
                ${historyList.map((h, idx) => `
                  <div style="background: var(--ct-track-bg); border: 1px solid var(--ct-border-color); border-radius: 8px; padding: 8px 12px; font-size: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: var(--ct-text-primary); margin-bottom: 3px;">
                      <span>第 ${idx + 1} 次周期</span>
                      <span style="color: var(--primary-color, #0284c7);">${h.duration_desc || ''}</span>
                    </div>
                    <div style="color: var(--ct-text-secondary); font-size: 11px;">
                      时间: ${this._formatYM(h.start_date)} ~ ${this._formatYM(h.end_date)}
                    </div>
                    ${h.note ? `<div style="color: var(--ct-text-secondary); font-size: 11px; margin-top: 3px;">备注: ${h.note}</div>` : ''}
                  </div>
                `).join('')}
              </div>
            `}
          </div>

          <div class="modal-actions" style="justify-content: flex-end;">
            <button type="button" class="btn-save" id="closeHistoryBtn">关闭</button>
          </div>
        </div>
      </div>
    `;
  }

  _bindEvents() {
    const root = this.shadowRoot;

    // 测试通知按钮 (🔔)
    const testNotifyBtn = root.querySelector('#testNotifyBtn');
    if (testNotifyBtn) {
      testNotifyBtn.onclick = async () => {
        if (testNotifyBtn.classList.contains('loading')) return;
        testNotifyBtn.classList.add('loading');
        testNotifyBtn.title = '正在发送通知...';
        try {
          let res = null;
          // 优先通过 WebSocket 发送总览报告
          if (this._hass && this._hass.callWS) {
            res = await this._hass.callWS({
              type: 'consumable_tracking/send_summary',
              force: true
            });
          } else if (this._hass && this._hass.callService) {
            await this._hass.callService('consumable_tracking', 'send_summary', { force: true });
          }
          alert('耗材全量使用总览通知已成功发送！请在企业微信中查收。');
        } catch (err) {
          console.error('发送通知失败:', err);
          let errText = err && (err.message || err.error || err.code || JSON.stringify(err));
          alert('发送通知失败: ' + errText);
        } finally {
          testNotifyBtn.classList.remove('loading');
          testNotifyBtn.title = '发送全量耗材总览通知到企业微信 (测试)';
        }
      };
    }

    // 拖拽排序逻辑 (Drag and Drop)
    const itemCards = root.querySelectorAll('.item-card');
    itemCards.forEach(card => {
      card.addEventListener('dragstart', (e) => {
        this._draggedId = card.dataset.id;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', card.dataset.id);
      });

      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        itemCards.forEach(c => {
          c.classList.remove('drag-over-top', 'drag-over-bottom');
        });
        this._draggedId = null;
      });

      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (!this._draggedId || this._draggedId === card.dataset.id) return;

        const rect = card.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (e.clientY < midY) {
          card.classList.add('drag-over-top');
          card.classList.remove('drag-over-bottom');
        } else {
          card.classList.add('drag-over-bottom');
          card.classList.remove('drag-over-top');
        }
      });

      card.addEventListener('dragleave', () => {
        card.classList.remove('drag-over-top', 'drag-over-bottom');
      });

      card.addEventListener('drop', async (e) => {
        e.preventDefault();
        const targetId = card.dataset.id;
        const draggedId = this._draggedId || e.dataTransfer.getData('text/plain');
        card.classList.remove('drag-over-top', 'drag-over-bottom');
        if (!draggedId || draggedId === targetId) return;

        const rect = card.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        const insertBefore = e.clientY < midY;

        // 计算新顺序数组
        const currentIds = this._items.map(i => i.id);
        const fromIdx = currentIds.indexOf(draggedId);
        if (fromIdx === -1) return;
        currentIds.splice(fromIdx, 1);

        let toIdx = currentIds.indexOf(targetId);
        if (!insertBefore) {
          toIdx += 1;
        }
        currentIds.splice(toIdx, 0, draggedId);

        // 前端立刻重排并更新显示
        const itemMap = new Map(this._items.map(i => [i.id, i]));
        this._items = currentIds.map(id => itemMap.get(id)).filter(Boolean);
        this._render();

        // 异步保存到后端存储
        await this._saveReorder(currentIds);
      });
    });

    // 新建按钮
    const addBtn = root.querySelector('#openAddBtn');
    if (addBtn) {
      addBtn.onclick = () => {
        this._editItem = null;
        this._showModal = true;
        this._render();
      };
    }

    // 分类筛选
    root.querySelectorAll('.chip').forEach(chip => {
      chip.onclick = () => {
        this._filterCategory = chip.dataset.cat;
        this._render();
      };
    });

    // 卡片动作按钮（历史、重置、编辑、删除）
    root.querySelectorAll('.btn-history, .btn-replace, .btn-icon').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const itemId = btn.dataset.id;
        const item = this._items.find(i => i.id === itemId);

        if (action === 'history' && item) {
          this._historyTargetItem = item;
          this._showHistoryModal = true;
          this._render();
        } else if (action === 'reset' && item) {
          this._resetTargetItem = item;
          this._showResetModal = true;
          this._render();
        } else if (action === 'edit' && item) {
          this._editItem = item;
          this._showModal = true;
          this._render();
        } else if (action === 'delete') {
          if (confirm('确定要删除该耗材跟踪记录吗？')) {
            this._deleteItem(itemId);
          }
        }
      };
    });

    // 模态弹窗模板点击快捷填充
    root.querySelectorAll('.preset-btn').forEach(btn => {
      btn.onclick = () => {
        const tpl = btn.dataset.tpl;
        const nameInp = root.querySelector('#inp_name');
        const catInp = root.querySelector('#inp_category');
        const iconInp = root.querySelector('#inp_icon');
        const durInp = root.querySelector('#inp_duration_val');
        const unitInp = root.querySelector('#inp_duration_unit');

        if (tpl === 'water_filter') {
          if (nameInp) nameInp.value = '净水器RO滤芯';
          if (catInp) catInp.value = '滤芯';
          if (iconInp) iconInp.value = 'mdi:filter';
          if (durInp) durInp.value = 12;
          if (unitInp) unitInp.value = 'month';
        } else if (tpl === 'air_filter') {
          if (nameInp) nameInp.value = '新风系统滤网';
          if (catInp) catInp.value = '滤芯';
          if (iconInp) iconInp.value = 'mdi:air-filter';
          if (durInp) durInp.value = 6;
          if (unitInp) unitInp.value = 'month';
        } else if (tpl === 'sweeper') {
          if (nameInp) nameInp.value = '扫地机主刷与尘盒';
          if (catInp) catInp.value = '清洁维护';
          if (iconInp) iconInp.value = 'mdi:robot-vacuum';
          if (durInp) durInp.value = 3;
          if (unitInp) unitInp.value = 'month';
        } else if (tpl === 'battery') {
          if (nameInp) nameInp.value = '智能门锁/传感器电池';
          if (catInp) catInp.value = '电池';
          if (iconInp) iconInp.value = 'mdi:battery-charging-90';
          if (durInp) durInp.value = 12;
          if (unitInp) unitInp.value = 'month';
        } else if (tpl === 'sewer') {
          if (nameInp) nameInp.value = '下水道疏浚保养';
          if (catInp) catInp.value = '管道维护';
          if (iconInp) iconInp.value = 'mdi:pipe-wrench';
          if (durInp) durInp.value = 6;
          if (unitInp) unitInp.value = 'month';
        }
      };
    });

    // 模态弹窗取消与保存
    const modalCancel = root.querySelector('#modalCancelBtn');
    if (modalCancel) {
      modalCancel.onclick = () => {
        this._showModal = false;
        this._editItem = null;
        this._render();
      };
    }

    const modalSave = root.querySelector('#modalSaveBtn');
    if (modalSave) {
      modalSave.onclick = () => {
        this._saveModalData();
      };
    }

    // 重置更换确认
    const resetCancel = root.querySelector('#resetCancelBtn');
    if (resetCancel) {
      resetCancel.onclick = () => {
        this._showResetModal = false;
        this._resetTargetItem = null;
        this._render();
      };
    }

    const resetConfirm = root.querySelector('#resetConfirmBtn');
    if (resetConfirm) {
      resetConfirm.onclick = () => {
        const item = this._resetTargetItem;
        if (!item) return;
        const startYM = root.querySelector('#reset_start_ym')?.value;
        const note = root.querySelector('#reset_note')?.value || '';
        this._resetItem(item.id, startYM, note);
      };
    }

    // 历史弹窗关闭事件
    const closeHistoryBtn = root.querySelector('#closeHistoryBtn');
    const closeHistoryIconBtn = root.querySelector('#closeHistoryIconBtn');
    const historyOverlay = root.querySelector('#historyModalOverlay');

    const closeHistory = () => {
      this._showHistoryModal = false;
      this._historyTargetItem = null;
      this._render();
    };

    if (closeHistoryBtn) closeHistoryBtn.onclick = closeHistory;
    if (closeHistoryIconBtn) closeHistoryIconBtn.onclick = closeHistory;
    if (historyOverlay) {
      historyOverlay.onclick = (e) => {
        if (e.target === historyOverlay) closeHistory();
      };
    }
  }

  async _saveModalData() {
    const root = this.shadowRoot;
    const name = root.querySelector('#inp_name')?.value?.trim();
    if (!name) {
      alert('请输入耗材名称！');
      return;
    }

    const itemData = {
      id: this._editItem ? this._editItem.id : undefined,
      name: name,
      category: root.querySelector('#inp_category')?.value?.trim() || '通用',
      icon: root.querySelector('#inp_icon')?.value?.trim() || 'mdi:package-variant',
      start_date: root.querySelector('#inp_start_date')?.value || this._getTodayYM(),
      duration_value: parseInt(root.querySelector('#inp_duration_val')?.value, 10) || 12,
      duration_unit: root.querySelector('#inp_duration_unit')?.value || 'month',
      note: root.querySelector('#inp_note')?.value?.trim() || '',
      history: this._editItem ? this._editItem.history : []
    };

    try {
      await this._hass.callWS({
        type: 'consumable_tracking/save_item',
        item: itemData
      });
      this._showModal = false;
      this._editItem = null;
      await this._fetchItems();
    } catch (err) {
      console.error('保存失败:', err);
      // 尝试通过 HA 服务添加
      await this._hass.callService('consumable_tracking', this._editItem ? 'update_item' : 'add_item', itemData);
      this._showModal = false;
      this._editItem = null;
      setTimeout(() => this._fetchItems(), 500);
    }
  }

  async _saveReorder(orderedIds) {
    try {
      if (this._hass && this._hass.callWS) {
        await this._hass.callWS({
          type: 'consumable_tracking/reorder_items',
          ordered_ids: orderedIds
        });
      } else if (this._hass && this._hass.callService) {
        await this._hass.callService('consumable_tracking', 'reorder_items', {
          ordered_ids: orderedIds
        });
      }
    } catch (err) {
      console.error('保存排序失败:', err);
    }
  }

  async _deleteItem(itemId) {
    try {
      await this._hass.callWS({
        type: 'consumable_tracking/delete_item',
        item_id: itemId
      });
      await this._fetchItems();
    } catch (err) {
      console.error('删除失败:', err);
      await this._hass.callService('consumable_tracking', 'delete_item', { item_id: itemId });
      setTimeout(() => this._fetchItems(), 500);
    }
  }

  async _resetItem(itemId, newStartDate, note) {
    try {
      await this._hass.callWS({
        type: 'consumable_tracking/reset_item',
        item_id: itemId,
        new_start_date: newStartDate,
        note: note
      });
      this._showResetModal = false;
      this._resetTargetItem = null;
      await this._fetchItems();
    } catch (err) {
      console.error('重置失败:', err);
      await this._hass.callService('consumable_tracking', 'reset_item', {
        item_id: itemId,
        new_start_date: newStartDate,
        note: note
      });
      this._showResetModal = false;
      this._resetTargetItem = null;
      setTimeout(() => this._fetchItems(), 500);
    }
  }
}

if (!customElements.get('consumable-tracking-card')) {
  customElements.define('consumable-tracking-card', ConsumableTrackingCard);
}

if (!window.customCards) {
  window.customCards = [];
}
if (!window.customCards.some(c => c.type === 'consumable-tracking-card')) {
  window.customCards.push({
    type: 'consumable-tracking-card',
    name: '耗材与事务跟踪卡片 (Consumable Tracking Card)',
    description: '家庭滤芯、电池、疏浚管道等各类耗材与周期的现代紧凑进度条跟踪卡片',
    preview: true
  });
}
