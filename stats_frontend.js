// Sistema de estadísticas por fuente
// Se agrega a superseller.html

function calcularStats(items) {
  const stats = {
    keywords: { encontrados: 0, fuente: 'keyword' },
    urls: { encontrados: 0, fuente: 'url_fija' },
    telegram: { encontrados: 0, fuente: 'telegram' }
  };

  items.forEach(item => {
    const tipo = item.source_type || '';
    if (tipo === 'keyword') stats.keywords.encontrados++;
    else if (tipo === 'url_fija') stats.urls.encontrados++;
    else if (tipo === 'telegram') stats.telegram.encontrados++;
  });

  return stats;
}

function renderStats(items) {
  const stats = calcularStats(items);

  let html = `
    <div style="margin-top:20px;padding:16px;background:rgba(26,48,78,.4);border-radius:8px;border:1px solid rgba(233,69,96,.3);">
      <div style="font-size:10px;font-weight:700;color:var(--red);letter-spacing:.8px;text-transform:uppercase;margin-bottom:12px;">
        📊 RESUMEN DE FUENTES
      </div>
  `;

  // Keywords
  if (stats.keywords.encontrados > 0) {
    html += `
      <div style="margin-bottom:10px;padding:8px;background:rgba(0,0,0,.2);border-radius:6px;">
        <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">
          🔤 KEYWORDS
        </div>
        <div style="font-size:11px;color:var(--t2);padding-left:20px;">
          └─ Productos finales: <span style="color:#10b981;font-weight:600;">${stats.keywords.encontrados}</span>
        </div>
      </div>
    `;
  }

  // URLs
  if (stats.urls.encontrados > 0) {
    html += `
      <div style="margin-bottom:10px;padding:8px;background:rgba(0,0,0,.2);border-radius:6px;">
        <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">
          🔗 URLs FIJAS
        </div>
        <div style="font-size:11px;color:var(--t2);padding-left:20px;">
          └─ Productos finales: <span style="color:#10b981;font-weight:600;">${stats.urls.encontrados}</span>
        </div>
      </div>
    `;
  }

  // Telegram
  if (stats.telegram.encontrados > 0) {
    html += `
      <div style="margin-bottom:10px;padding:8px;background:rgba(0,0,0,.2);border-radius:6px;">
        <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">
          📱 TELEGRAM
        </div>
        <div style="font-size:11px;color:var(--t2);padding-left:20px;">
          └─ Productos finales: <span style="color:#10b981;font-weight:600;">${stats.telegram.encontrados}</span>
        </div>
      </div>
    `;
  }

  html += `</div>`;

  return html;
}
