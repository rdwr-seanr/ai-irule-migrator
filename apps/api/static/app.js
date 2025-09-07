(() => {
  const apiBase = window.__API_BASE__ || '';

  // Utils
  const $ = (id) => document.getElementById(id);
  const setStatus = (el, msg, kind = 'info') => {
    el.classList.remove('error', 'success', 'info');
    el.classList.add(kind);
    el.textContent = msg;
  };
  const toJSON = (o) => JSON.stringify(o, null, 2);
  const show = (el) => el.classList.remove('hidden');
  const hide = (el) => el.classList.add('hidden');

  // Migrate
  const migrateBtn = $('migrateBtn');
  migrateBtn?.addEventListener('click', async () => {
    const fileInput = $('iruleFile');
    const status = $('migrateStatus');
    const resultBox = $('migrateResult');
    const scriptEl = $('script');
    const reportEl = $('report');
    hide(resultBox);

    if (!fileInput.files || fileInput.files.length === 0) {
      setStatus(status, 'Please select a .tcl or .txt iRule file.', 'error');
      return;
    }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    setStatus(status, 'Uploading and starting migration…');
    try {
      const resp = await fetch(`${apiBase}/v1/migrate`, { method: 'POST', body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const { run_id } = await resp.json();
      setStatus(status, `Started: ${run_id}. Waiting for completion…`);
      // poll
      let done = false;
      let attempts = 0;
      while (!done && attempts < 120) {
        await new Promise((r) => setTimeout(r, 1000));
        const s = await fetch(`${apiBase}/v1/migrate/${run_id}`);
        const data = await s.json();
        if (data.status === 'completed' || data.status === 'failed') {
          done = true;
          const outputs = data.outputs || {};
          const script = (outputs.script) || (outputs.report && outputs.report.script) || '';
          const report = outputs.report || outputs || {};
          scriptEl.textContent = script || '# (no script)';
          reportEl.textContent = toJSON(report);
          show(resultBox);
          setStatus(status, data.status === 'completed' ? 'Completed' : 'Failed', data.status === 'completed' ? 'success' : 'error');
          break;
        }
        attempts++;
      }
      if (!done) setStatus(status, 'Timed out waiting for result', 'error');
    } catch (e) {
      setStatus(status, `Error: ${e}`, 'error');
    }
  });

  $('copyScript')?.addEventListener('click', async () => {
    try {
      const txt = $('script').textContent || '';
      await navigator.clipboard.writeText(txt);
      alert('Copied script to clipboard');
    } catch {}
  });

  // QA
  $('qaBtn')?.addEventListener('click', async () => {
    const q = $('qaQuestion').value.trim();
    const status = $('qaStatus');
    const resultBox = $('qaResult');
    const answerEl = $('answer');
    const citesEl = $('citations');
    hide(resultBox);
    if (!q) { setStatus(status, 'Enter a question', 'error'); return; }
    setStatus(status, 'Searching…');
    try {
      const resp = await fetch(`${apiBase}/v1/qa`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) });
      const data = await resp.json();
      answerEl.textContent = data.answer || '(no answer)';
      citesEl.innerHTML = '';
      (data.citations || []).forEach((c) => {
        const li = document.createElement('li');
        const title = c.title || c.doc_id || 'document';
        const loc = c.page_or_slide ? ` (p/slide ${c.page_or_slide})` : '';
        li.textContent = `${title}${loc}`;
        citesEl.appendChild(li);
      });
      show(resultBox);
      setStatus(status, 'Done', 'success');
    } catch (e) {
      setStatus(status, `Error: ${e}`, 'error');
    }
  });

  // Ingest
  $('ingestBtn')?.addEventListener('click', async () => {
    const files = $('docsFiles').files;
    const tags = $('tags').value.trim();
    const replace = $('replace').checked;
    const status = $('ingestStatus');
    const resultBox = $('ingestResult');
    const reportEl = $('ingestReport');
    hide(resultBox);
    if (!files || files.length === 0) { setStatus(status, 'Select one or more docs', 'error'); return; }
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append('files', f));
    fd.append('replace', String(replace));
    if (tags) fd.append('tags', tags);
    setStatus(status, 'Uploading & indexing…');
    try {
      const resp = await fetch(`${apiBase}/v1/ingest`, { method: 'POST', body: fd });
      const { job_id } = await resp.json();
      setStatus(status, `Job ${job_id} started…`);
      let done = false; let attempts = 0;
      while (!done && attempts < 120) {
        await new Promise((r) => setTimeout(r, 1000));
        const s = await fetch(`${apiBase}/v1/ingest/${job_id}`);
        const data = await s.json();
        if (data.status === 'completed' || data.status === 'failed') {
          done = true;
          reportEl.textContent = toJSON(data.result || data);
          show(resultBox);
          setStatus(status, data.status === 'completed' ? 'Completed' : 'Failed', data.status === 'completed' ? 'success' : 'error');
          break;
        }
        attempts++;
      }
      if (!done) setStatus(status, 'Timed out waiting for job', 'error');
    } catch (e) {
      setStatus(status, `Error: ${e}`, 'error');
    }
  });
})();

