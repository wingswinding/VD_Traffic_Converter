document.addEventListener('DOMContentLoaded', () => {
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

  const linksTextarea = document.getElementById('linksTextarea');
  const saveLinksBtn = document.getElementById('saveLinksBtn');
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

  dateInput.addEventListener('change', updateDayBadge);
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
        setTimeout(initCharts, 100);
      }
    });
  });

  // 4. Run Analysis Execution
  runBtn.addEventListener('click', async () => {
    const rawDate = dateInput.value.replace(/-/g, '');
    const mode = timeModeSelect.value;
    const customHours = customHoursInput.value.trim();

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
            loadReports();
            loadLogs();
            initCharts();
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

  // 5. Load & Save Links
  async function loadLinks() {
    try {
      const resp = await fetch('/api/links');
      const data = await resp.json();
      linksTextarea.value = data.links.join('\n');
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
      }
    } catch (err) {
      alert('儲存失敗');
    }
  });

  // 6. Reports List
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

  // 7. Logs List
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

  // 8. Load References
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

  // 9. Render Interactive ECharts
  function initCharts() {
    if (!vcChart) {
      vcChart = echarts.init(document.getElementById('vcChart'));
    }
    if (!speedChart) {
      speedChart = echarts.init(document.getElementById('speedChart'));
    }

    const segments = ['大園-大竹', '大竹-機場系統', '機場系統-南桃園', '南桃園-大湳', '大湳-鶯歌系統'];

    const vcOption = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { textStyle: { color: '#94a3b8' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: segments, axisLine: { lineStyle: { color: '#475569' } } },
      yAxis: { type: 'value', max: 1.2, axisLine: { lineStyle: { color: '#475569' } }, splitLine: { lineStyle: { color: '#1e293b' } } },
      series: [
        { name: '晨峰 V/C', type: 'bar', data: [0.65, 0.72, 0.96, 0.84, 0.78], itemStyle: { color: '#00f2fe' } },
        { name: '昏峰 V/C', type: 'bar', data: [0.68, 0.75, 0.91, 0.88, 0.82], itemStyle: { color: '#4facfe' } }
      ]
    };

    const speedOption = {
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#94a3b8' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: segments, axisLine: { lineStyle: { color: '#475569' } } },
      yAxis: { type: 'value', min: 40, max: 110, axisLine: { lineStyle: { color: '#475569' } }, splitLine: { lineStyle: { color: '#1e293b' } } },
      series: [
        { name: '晨峰速率 (KPH)', type: 'line', smooth: true, data: [92.5, 88.0, 56.4, 72.1, 84.6], itemStyle: { color: '#34d399' } },
        { name: '昏峰速率 (KPH)', type: 'line', smooth: true, data: [89.0, 85.2, 61.8, 68.9, 81.3], itemStyle: { color: '#f59e0b' } }
      ]
    };

    vcChart.setOption(vcOption);
    speedChart.setOption(speedOption);

    renderMockLOSTable();
  }

  function renderMockLOSTable() {
    const tbody = document.getElementById('losTableBody');
    const rows = [
      { name: '國道2號 (大園-大竹)', dir: '往東', cap: 7400, limit: 100, mpcu: 4810, mvc: 0.65, mspd: 92.5, mlos: 'C2', epcu: 5032, evc: 0.68, espd: 89.0, elos: 'C2' },
      { name: '國道2號 (大竹-機場系統)', dir: '往東', cap: 7400, limit: 100, mpcu: 5328, mvc: 0.72, mspd: 88.0, mlos: 'C2', epcu: 5550, evc: 0.75, espd: 85.2, elos: 'C2' },
      { name: '國道2號 (機場系統-南桃園)', dir: '往東', cap: 6760, limit: 100, mpcu: 6490, mvc: 0.96, mspd: 56.4, mlos: 'E4', epcu: 6152, evc: 0.91, espd: 61.8, elos: 'E3' },
      { name: '國道2號 (南桃園-大湳)', dir: '往東', cap: 6760, limit: 100, mpcu: 5678, mvc: 0.84, mspd: 72.1, mlos: 'D3', epcu: 5948, evc: 0.88, espd: 68.9, elos: 'D3' },
      { name: '國道2號 (大園交流道出口)', dir: '往東', cap: 3800, limit: 50, mpcu: 1250, mvc: 0.33, mspd: 46.5, mlos: 'B1', epcu: 1480, evc: 0.39, espd: 45.2, elos: 'B1' },
    ];

    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      const losClassM = r.mlos.startsWith('A') || r.mlos.startsWith('B') ? 'los-A' : (r.mlos.startsWith('C') || r.mlos.startsWith('D') ? 'los-C' : 'los-E');
      const losClassE = r.elos.startsWith('A') || r.elos.startsWith('B') ? 'los-A' : (r.elos.startsWith('C') || r.elos.startsWith('D') ? 'los-C' : 'los-E');

      tr.innerHTML = `
        <td style="text-align:left; font-weight:600;">${r.name}</td>
        <td>${r.dir}</td>
        <td>${r.cap.toLocaleString()}</td>
        <td>${r.limit}</td>
        <td>${r.mpcu.toLocaleString()}</td>
        <td>${r.mvc.toFixed(2)}</td>
        <td>${r.mspd.toFixed(1)}</td>
        <td><span class="los-badge ${losClassM}">${r.mlos}</span></td>
        <td>${r.epcu.toLocaleString()}</td>
        <td>${r.evc.toFixed(2)}</td>
        <td>${r.espd.toFixed(1)}</td>
        <td><span class="los-badge ${losClassE}">${r.elos}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Window Resize for ECharts
  window.addEventListener('resize', () => {
    if (vcChart) vcChart.resize();
    if (speedChart) speedChart.resize();
  });

  // Initial Load
  loadLinks();
  loadReports();
  loadLogs();
  loadReferences();
  initCharts();
});
