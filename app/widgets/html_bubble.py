"""A compact, self-contained interactive HTML Bubble demo."""

HTML_BUBBLE = r'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root { color-scheme: light dark; --accent: #6c63ff; --card: #ffffff; --ink: #20212b; --muted: #737583; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 18px; background: transparent; color: var(--ink); font: 15px/1.45 system-ui, sans-serif; }
    .widget { max-width: 520px; margin: auto; padding: 20px; border-radius: 22px; background: var(--card); box-shadow: 0 8px 28px #0002; }
    .top { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .eyebrow { color:var(--accent); font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
    h1 { margin:4px 0 8px; font-size:22px; }
    p { margin:0 0 16px; color:var(--muted); }
    button { border:0; border-radius:12px; padding:10px 14px; background:var(--accent); color:#fff; font:inherit; font-weight:650; cursor:pointer; }
    button.secondary { padding:8px 10px; background:#eeeeF7; color:#343344; }
    .items { display:grid; gap:9px; margin:18px 0; }
    label { display:flex; align-items:center; gap:11px; padding:12px; border:1px solid #8883; border-radius:13px; cursor:pointer; }
    input { width:18px; height:18px; accent-color:var(--accent); }
    .footer { display:flex; justify-content:space-between; align-items:center; gap:12px; }
    #status { min-height:22px; color:var(--muted); font-size:13px; }
    @media (prefers-color-scheme: dark) { :root { --card:#24252d; --ink:#f4f4f7; --muted:#b3b4c0; } button.secondary { background:#393a46; color:#f4f4f7; } }
  </style>
</head>
<body>
  <main class="widget" id="widget">
    <div class="top">
      <div><div class="eyebrow">HTML Bubble · интерактивное демо</div><h1>План на сегодня</h1></div>
      <button class="secondary" id="theme" type="button" aria-label="Сменить акцент">🎨</button>
    </div>
    <p>Проверьте интерактивность, стили и локальное состояние внутри сообщения.</p>
    <section class="items" aria-label="Задачи">
      <label><input type="checkbox"> <span>Интерактивные элементы формы</span></label>
      <label><input type="checkbox"> <span>Стили и адаптивная раскладка</span></label>
      <label><input type="checkbox"> <span>Обновление интерфейса без нового сообщения</span></label>
    </section>
    <div class="footer"><span id="status" aria-live="polite">Отмечено: 0 из 3</span><button id="celebrate" type="button">Готово ✨</button></div>
  </main>
  <script>
    (() => {
      const checks = [...document.querySelectorAll('input[type="checkbox"]')];
      const status = document.getElementById('status');
      const colors = ['#6c63ff', '#007f73', '#d04a7b', '#d17b00'];
      let colorIndex = 0;
      const update = () => {
        const done = checks.filter((check) => check.checked).length;
        status.textContent = `Отмечено: ${done} из ${checks.length}`;
      };
      checks.forEach((check) => check.addEventListener('change', update));
      document.getElementById('theme').addEventListener('click', () => {
        colorIndex = (colorIndex + 1) % colors.length;
        document.documentElement.style.setProperty('--accent', colors[colorIndex]);
      });
      document.getElementById('celebrate').addEventListener('click', (event) => {
        const done = checks.filter((check) => check.checked).length;
        status.textContent = done === checks.length ? 'Все пункты выполнены! Отличная работа 🎉' : `Готово ${done} из ${checks.length} — можно продолжить`;
        event.currentTarget.textContent = done === checks.length ? 'Ура! 🎉' : 'Продолжаю →';
      });
    })();
  </script>
</body>
</html>'''
