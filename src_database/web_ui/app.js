document.addEventListener('DOMContentLoaded', () => {
  // Global Raw Results Cache
  let rawAnalysisResults = null;
  let rawMetadataList = [];
  let currentAnalyzingDate = '';

  // Elements
  const dateInput = document.getElementById('analysisDate');
  const dayTypeBadge = document.getElementById('dayTypeBadge');
  const timeModeSelect = document.getElementById('timeMode');
  const customHoursGroup = document.getElementById('customHoursGroup');
  const customHoursInput = document.getElementById('customHoursInput');
  const runBtn = document.getElementById('runBtn');

  const progressContainer = document.getElementById('progressContainer');
  const progressTitle = document.getElementById('progressTitle');
  const progressPercent = document.getElementById('progressPercent');
  const progressBarFill = document.getElementById('progressBarFill');
  const terminalOutput = document.getElementById('terminalOutput');
  const consoleAccordion = document.getElementById('consoleAccordion');

  // Dashboard KPI Elements
  const statTotalLinks = document.getElementById('statTotalLinks');
  const statSubLinks = document.getElementById('statSubLinks');
  const statMaxVC = document.getElementById('statMaxVC');
  const statMaxVCSeg = document.getElementById('statMaxVCSeg');
  const statWorstLOS = document.getElementById('statWorstLOS');
  const statLatestReportLink = document.getElementById('statLatestReportLink');

  // Filter Elements
  const filterHighway = document.getElementById('filterHighway');
  const filterType = document.getElementById('filterType');
  const filterDir = document.getElementById('filterDir');
  const filterKeyword = document.getElementById('filterKeyword');

  // Links Tab Elements
  const linksTextarea = document.getElementById('linksTextarea');
  const saveLinksBtn = document.getElementById('saveLinksBtn');
  const linksCountBadge = document.getElementById('linksCountBadge');
  const linksMetadataBody = document.getElementById('linksMetadataBody');

  // Reports & Logs Elements
  const reportsList = document.getElementById('reportsList');
  const logsList = document.getElementById('logsList');
  const logViewerContent = document.getElementById('logViewerContent');
  const referenceGrid = document.getElementById('referenceGrid');

  let pollTimer = null;
  let vcChart = null;
  let speedChart = null;

  // 1. Date Change Handler
  function updateDayBadge() {
    const dateVal = dateInput.value;
    if (!dateVal) return;
    const dt = new Date(dateVal);
    const day = dt.getDay(); // 0: Sun, 6: Sat
    if (day === 0 || day === 6) {
      dayTypeBadge.textContent = '假日 / 節慶峰期';
      dayTypeBadge.style.background = 'rgba(245, 158, 11, 0.2)';
      dayTypeBadge.style.color = '#f59e0b';
    } else {
      dayTypeBadge.textContent = '平常日 (一~五)';
      dayTypeBadge.style.background = 'rgba(0, 242, 254, 0.15)';
      dayTypeBadge.style.color = '#00f2fe';
    }
  }

  dateInput.addEventListener('change', () => {
    updateDayBadge();
    const rawDate = dateInput.value.replace(/-/g, '');
    loadLatestResults(rawDate);
  });
  updateDayBadge();

  // 2. Time Mode Handler
  timeModeSelect.addEventListener('change', () => {
    if (timeModeSelect.value === 'custom') {
      customHoursGroup.classList.remove('hidden');
    } else {
      customHoursGroup.classList.add('hidden');
    }
  });

  // 3. Tab Switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      document.getElementById(`tab-${tabId}`).classList.add('active');

      if (tabId === 'dashboard') {
        setTimeout(renderDashboardView, 100);
      } else if (tabId === 'links') {
        loadLinkMetadata();
      }
    });
  });

  // 4. Run Analysis Execution
  runBtn.addEventListener('click', async () => {
    const rawDate = dateInput.value.replace(/-/g, '');
    const mode = timeModeSelect.value;
    const customHours = customHoursInput.value.trim();
    currentAnalyzingDate = rawDate;

    runBtn.disabled = true;
    runBtn.textContent = '⏳ 分析執行中...';
    progressContainer.classList.remove('hidden');
    consoleAccordion.open = true;

    try {
      const resp = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: rawDate, mode: mode, custom_hours: customHours })
      });
      const data = await resp.json();
      if (resp.ok) {
        startPollingProgress();
      } else {
        alert(data.error || '無法啟動分析任務');
        resetRunButton();
      }
    } catch (err) {
      alert('無法連接到後端伺服器');
      resetRunButton();
    }
  });

  function startPollingProgress() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        const resp = await fetch('/api/progress');
        const data = await resp.json();

        progressPercent.textContent = `${data.progress}%`;
        progressBarFill.style.width = `${data.progress}%`;
        progressTitle.textContent = data.message || '正在處理中...';

        if (data.logs && data.logs.length > 0) {
          terminalOutput.textContent = data.logs.join('\n');
          terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }

        if (data.status === 'completed' || data.status === 'error') {
          clearInterval(pollTimer);
          resetRunButton();
          if (data.status === 'completed') {
            loadLatestResults(currentAnalyzingDate);
            loadReports();
            loadLogs();
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, 800);
  }

  function resetRunButton() {
    runBtn.disabled = false;
    runBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> 🚀 開始執行轉檔分析`;
  }

  // 5. Fetch Excel Analysis Results for Selected or Latest Date
  async function loadLatestResults(targetDate = '') {
    try {
      const url = targetDate ? `/api/latest_results?date=${encodeURIComponent(targetDate)}` : '/api/latest_results';
      const resp = await fetch(url);
      const data = await resp.json();
      if (!data || !data.data) return;

      rawAnalysisResults = data;

      // Update Top KPIs
      statTotalLinks.textContent = `${data.total_links} 筆`;
      statSubLinks.textContent = `主線 ${data.mainline_count} 筆 | 匝道 ${data.ramp_count} 筆`;
      statMaxVC.textContent = data.max_vc.toFixed(2);
      statMaxVCSeg.textContent = data.max_vc_seg;
      statWorstLOS.textContent = data.worst_los;

      // Update Download Link
      statLatestReportLink.textContent = `${data.report_name} ⬇️`;
      statLatestReportLink.href = `/api/download?file=${encodeURIComponent(data.report_name)}`;

      // Update Highway Filter Options (Removed 流域/)
      if (data.highways && data.highways.length > 0) {
        filterHighway.innerHTML = '<option value="ALL">🛣️ 國道路線選單 (全選)</option>';
        data.highways.forEach(hw => {
          const opt = document.createElement('option');
          opt.value = hw;
          opt.textContent = hw;
          filterHighway.appendChild(opt);
        });
      }

      renderDashboardView();
    } catch (err) {
      console.error(err);
    }
  }

  // Filter Event Listeners
  [filterHighway, filterType, filterDir, filterKeyword].forEach(el => {
    el.addEventListener('input', renderDashboardView);
    el.addEventListener('change', renderDashboardView);
  });

  function getFilteredResults() {
    if (!rawAnalysisResults || !rawAnalysisResults.data) return [];
    const hwVal = filterHighway.value;
    const typeVal = filterType.value;
    const dirVal = filterDir.value;
    const kwVal = filterKeyword.value.trim().toLowerCase();

    return rawAnalysisResults.data.filter(item => {
      if (hwVal !== 'ALL' && item.road_name !== hwVal) return false;
      if (typeVal !== 'ALL' && item.type !== typeVal) return false;
      if (dirVal !== 'ALL' && item.direction !== dirVal) return false;
      if (kwVal && !item.segment.toLowerCase().includes(kwVal) && !item.road_name.toLowerCase().includes(kwVal)) return false;
      return true;
    });
  }

  function renderDashboardView() {
    const filtered = getFilteredResults();
    renderTable(filtered);
    renderCharts(filtered);
  }

  // 6. Render Full-Width ECharts with Dynamic Y-axis Max for V/C
  function renderCharts(items) {
    if (!vcChart) vcChart = echarts.init(document.getElementById('vcChart'));
    if (!speedChart) speedChart = echarts.init(document.getElementById('speedChart'));

    const labels = items.map(x => `${x.segment}\n(${x.direction})`);
    const morningVC = items.map(x => x.m_vc);
    const eveningVC = items.map(x => x.e_vc);

    const morningSpd = items.map(x => x.m_speed);
    const eveningSpd = items.map(x => x.e_speed);
    const speedLimits = items.map(x => x.speed_limit);

    // Dynamic V/C Y-axis Max Calculation (Max V/C in results + 0.20)
    const maxRawVC = Math.max(...morningVC, ...eveningVC, 0);
    const dynamicYMax = Math.max(1.0, Math.ceil((maxRawVC + 0.20) * 100) / 100);

    const vcOption = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { textStyle: { color: '#94a3b8' } },
      grid: { left: '3%', right: '3%', bottom: '15%', containLabel: true },
      dataZoom: [
        { type: 'slider', show: true, start: 0, end: 100, textStyle: { color: '#94a3b8' } },
        { type: 'inside', start: 0, end: 100 }
      ],
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: '#cbd5e1', interval: 0, rotate: 25, fontSize: 11 },
        axisLine: { lineStyle: { color: '#475569' } }
      },
      yAxis: {
        type: 'value',
        name: `V/C 比值 (上限 ${dynamicYMax})`,
        max: dynamicYMax,
        nameTextStyle: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#475569' } },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [
        { name: '晨峰 V/C', type: 'bar', data: morningVC, itemStyle: { color: '#00f2fe' } },
        { name: '昏峰 V/C', type: 'bar', data: eveningVC, itemStyle: { color: '#4facfe' } }
      ]
    };

    const speedOption = {
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#94a3b8' } },
      grid: { left: '3%', right: '3%', bottom: '15%', containLabel: true },
      dataZoom: [
        { type: 'slider', show: true, start: 0, end: 100, textStyle: { color: '#94a3b8' } },
        { type: 'inside', start: 0, end: 100 }
      ],
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: '#cbd5e1', interval: 0, rotate: 25, fontSize: 11 },
        axisLine: { lineStyle: { color: '#475569' } }
      },
      yAxis: {
        type: 'value',
        name: '車速 (KPH)',
        min: 30,
        max: 120,
        nameTextStyle: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#475569' } },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [
        { name: '晨峰車速 (KPH)', type: 'line', smooth: true, data: morningSpd, itemStyle: { color: '#34d399' } },
        { name: '昏峰車速 (KPH)', type: 'line', smooth: true, data: eveningSpd, itemStyle: { color: '#f59e0b' } },
        { name: '法定速限 (KPH)', type: 'line', step: 'middle', data: speedLimits, itemStyle: { color: '#ef4444' }, lineStyle: { type: 'dashed', width: 2 } }
      ]
    };

    vcChart.setOption(vcOption);
    speedChart.setOption(speedOption);

    vcChart.resize();
    speedChart.resize();
  }

  // 7. Render Complete LOS Table
  function renderTable(items) {
    const tbody = document.getElementById('losTableBody');
    tbody.innerHTML = '';

    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="13">符合條件無點位數據</td></tr>';
      return;
    }

    items.forEach((r, idx) => {
      const tr = document.createElement('tr');
      const losClassM = r.m_los.startsWith('A') || r.m_los.startsWith('B') ? 'los-A' : (r.m_los.startsWith('C') || r.m_los.startsWith('D') ? 'los-C' : 'los-E');
      const losClassE = r.e_los.startsWith('A') || r.e_los.startsWith('B') ? 'los-A' : (r.e_los.startsWith('C') || r.e_los.startsWith('D') ? 'los-C' : 'los-E');

      tr.innerHTML = `
        <td><span class="type-badge">${idx + 1} (${r.type})</span></td>
        <td style="text-align:left; font-weight:600;">${r.road_name} ${r.segment}</td>
        <td>${r.direction}</td>
        <td>${Math.round(r.capacity).toLocaleString()}</td>
        <td>${Math.round(r.speed_limit)}</td>
        <td>${Math.round(r.m_pcu).toLocaleString()}</td>
        <td>${r.m_vc.toFixed(2)}</td>
        <td>${r.m_speed.toFixed(1)}</td>
        <td><span class="los-badge ${losClassM}">${r.m_los}</span></td>
        <td>${Math.round(r.e_pcu).toLocaleString()}</td>
        <td>${r.e_vc.toFixed(2)}</td>
        <td>${r.e_speed.toFixed(1)}</td>
        <td><span class="los-badge ${losClassE}">${r.e_los}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 8. Load & Save Links with Metadata Preview
  async function loadLinks() {
    try {
      const resp = await fetch('/api/links');
      const data = await resp.json();
      linksTextarea.value = data.links.join('\n');
      loadLinkMetadata();
    } catch (err) {
      console.error(err);
    }
  }

  async function loadLinkMetadata() {
    try {
      const resp = await fetch('/api/link_metadata');
      const data = await resp.json();
      if (!data || !data.metadata) return;

      rawMetadataList = data.metadata;
      linksCountBadge.textContent = `共 ${rawMetadataList.length} 筆`;

      linksMetadataBody.innerHTML = '';
      rawMetadataList.forEach((m, idx) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td style="font-family:var(--font-mono); font-weight:600; color:var(--primary);">${m.link_id}</td>
          <td style="font-family:var(--font-mono);">${m.vd_id}</td>
          <td>${m.road_name}</td>
          <td>${m.direction}</td>
          <td><span class="type-badge">${m.type}</span></td>
          <td>${m.lanes} 車道</td>
        `;
        linksMetadataBody.appendChild(tr);
      });
    } catch (err) {
      console.error(err);
    }
  }

  saveLinksBtn.addEventListener('click', async () => {
    const rawText = linksTextarea.value;
    const links = rawText.split('\n').map(x => x.trim()).filter(x => x);
    try {
      const resp = await fetch('/api/save_links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ links: links })
      });
      if (resp.ok) {
        alert('路段設定檔已成功儲存！');
        loadLinkMetadata();
      }
    } catch (err) {
      alert('儲存失敗');
    }
  });

  // 9. Reports List
  async function loadReports() {
    try {
      const resp = await fetch('/api/reports');
      const data = await resp.json();
      reportsList.innerHTML = '';
      if (data.reports.length === 0) {
        reportsList.innerHTML = '<li class="file-item">尚無導出報表</li>';
        return;
      }
      data.reports.forEach(r => {
        const li = document.createElement('li');
        li.className = 'file-item';
        li.innerHTML = `
          <div>
            <strong>📄 ${r.name}</strong>
            <div style="font-size:0.75rem; color:#64748b;">修改時間: ${r.mtime} | 大小: ${r.size}</div>
          </div>
          <a class="btn btn-sm btn-secondary" href="/api/download?file=${encodeURIComponent(r.name)}" download>⬇️ 下載 Excel</a>
        `;
        reportsList.appendChild(li);
      });
    } catch (err) {
      console.error(err);
    }
  }

  // 10. Logs List
  async function loadLogs() {
    try {
      const resp = await fetch('/api/logs');
      const data = await resp.json();
      logsList.innerHTML = '';
      if (data.logs.length === 0) {
        logsList.innerHTML = '<li class="file-item">尚無歷程 Log</li>';
        return;
      }
      data.logs.forEach(l => {
        const li = document.createElement('li');
        li.className = 'file-item';
        li.style.cursor = 'pointer';
        li.innerHTML = `
          <div>
            <strong>📜 ${l.name}</strong>
            <div style="font-size:0.75rem; color:#64748b;">${l.mtime} | ${l.size}</div>
          </div>
        `;
        li.addEventListener('click', () => viewLogContent(l.name));
        logsList.appendChild(li);
      });
    } catch (err) {
      console.error(err);
    }
  }

  async function viewLogContent(filename) {
    try {
      const resp = await fetch(`/api/log_content?file=${encodeURIComponent(filename)}`);
      const data = await resp.json();
      document.getElementById('logViewerTitle').textContent = `檢視 Log: ${filename}`;
      logViewerContent.textContent = data.content || '文字無內容';
    } catch (err) {
      console.error(err);
    }
  }

  // 11. Load References
  async function loadReferences() {
    try {
      const resp = await fetch('/api/references');
      const data = await resp.json();
      referenceGrid.innerHTML = '';
      data.references.forEach(ref => {
        const li = document.createElement('li');
        li.className = 'ref-card';
        li.innerHTML = `
          <h4>📁 ${ref.name}</h4>
          <p style="font-size:0.8rem; color:#94a3b8;">大小: ${ref.size} (${ref.ext})</p>
        `;
        referenceGrid.appendChild(li);
      });
    } catch (err) {
      console.error(err);
    }
  }

  // Window Resize for ECharts
  window.addEventListener('resize', () => {
    if (vcChart) vcChart.resize();
    if (speedChart) speedChart.resize();
  });

  // Initial Load Trigger
  loadLinks();
  loadReports();
  loadLogs();
  loadReferences();
  const initialDate = dateInput.value.replace(/-/g, '');
  loadLatestResults(initialDate);
});
