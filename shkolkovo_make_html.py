import argparse
import json
import sys
import webbrowser
from pathlib import Path

SINGLE_OPTIONS = """        <option value="number">Поиск по номеру</option>
        <option value="text">Поиск по тексту</option>"""

ALL_OPTIONS = """        <option value="number">Поиск по номеру</option>
        <option value="ege">Поиск по номеру задания ЕГЭ</option>
        <option value="text">Поиск по тексту</option>"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__PAGE_TITLE__</title>
<style>
  :root {
    --accent: #4f6ef7;
    --accent-dark: #3a55d9;
    --bg: #f4f6fb;
    --card: #ffffff;
    --border: #e3e7f0;
    --text: #1f2430;
    --muted: #6b7280;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.55;
  }

  header {
    position: sticky; top: 0; z-index: 20;
    background: var(--card); border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(20,30,60,.06);
    padding: 14px 20px;
  }
  .header-inner { max-width: 960px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 12px; }
  h1 .sub { color: var(--muted); font-weight: 500; font-size: 14px; }
  .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  .controls select,
  .controls input[type="search"] {
    padding: 9px 14px; font-size: 15px; border: 1px solid var(--border);
    border-radius: 10px; outline: none; background: #fafbfe;
    transition: border-color .15s, box-shadow .15s;
  }
  .controls select:focus,
  .controls input[type="search"]:focus {
    border-color: var(--accent); box-shadow: 0 0 0 3px rgba(79,110,247,.15);
  }
  .controls select { min-width: 180px; }
  .controls input[type="search"] { flex: 1; min-width: 200px; }
  .btn {
    padding: 9px 14px; font-size: 14px; border: 1px solid var(--border);
    background: #fff; border-radius: 10px; cursor: pointer; color: var(--text);
    transition: background .15s;
  }
  .btn:hover { background: #eef1f9; }
  .btn-primary {
    background: var(--accent); color: #fff; border-color: var(--accent);
  }
  .btn-primary:hover { background: var(--accent-dark); border-color: var(--accent-dark); }
  .count { font-size: 13px; color: var(--muted); white-space: nowrap; }

  main { max-width: 960px; margin: 20px auto 80px; padding: 0 20px; }

  .task-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; margin-bottom: 18px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(20,30,60,.04);
  }
  .task-head {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    padding: 14px 18px; border-bottom: 1px solid var(--border);
    background: #fafbfe;
  }
  .badge {
    font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 999px;
  }
  .badge-num { background: var(--accent); color: #fff; }
  .badge-id  { background: #eef1f9; color: var(--muted); }
  .badge-ege { background: #e6f6ec; color: #177245; }
  .task-name { font-weight: 600; font-size: 15px; }
  .theme-path {
    padding: 10px 18px 0; font-size: 13px; color: var(--muted);
  }
  .task-meta { padding: 8px 18px 12px; display: flex; flex-direction: column; gap: 6px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    font-size: 12px; padding: 2px 9px; border-radius: 999px;
    background: #eef3ff; color: var(--accent-dark);
  }
  .chip-src { background: #fff4e5; color: #a05a00; }

  details.section { border-top: 1px solid var(--border); }
  details.section summary {
    cursor: pointer; padding: 11px 18px; font-weight: 600; font-size: 14px;
    color: var(--accent-dark); user-select: none; list-style: none;
    display: flex; align-items: center; gap: 8px;
  }
  details.section summary::-webkit-details-marker { display: none; }
  details.section summary::before {
    content: "▸"; transition: transform .15s; color: var(--accent);
  }
  details.section[open] summary::before { transform: rotate(90deg); }
  details.section .tex-content { padding: 4px 20px 18px; }

  .tex-content img { vertical-align: middle; max-width: 100%; }
  .tex-content img.math-display { display: block; margin: 12px auto; }
  .tex-content p { margin: .4em 0; }
  .tex-content p.indent { text-indent: 1.5em; }
  .tex-content table.tabular, .tex-content table { border-collapse: collapse; margin: 10px 0; }
  .tex-content td, .tex-content th { border: 1px solid #cbd2e0; padding: 6px 10px; }
  .tex-content .center { text-align: center; }
  .tex-content .labx-0900, .tex-content .labx-1000 { font-weight: bold; }
  .tex-content .lati-0900, .tex-content .lati-1000 { font-style: italic; }

  mark { background: #ffe58a; border-radius: 3px; padding: 0 2px; }

  #noResults {
    display: none; text-align: center; padding: 60px 20px; color: var(--muted);
  }
  #noResults .big { font-size: 46px; margin-bottom: 12px; }
  #noResults .msg { font-size: 18px; }

  #initialMessage {
    text-align: center; padding: 60px 20px; color: var(--muted);
  }
  #initialMessage .big { font-size: 46px; margin-bottom: 12px; }
  #initialMessage .msg { font-size: 18px; }
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <h1>__H1__ <span class="sub">· Физика · всего __TOTAL__</span></h1>
    <div class="controls">
      <select id="searchType">
__SEARCH_OPTIONS__
      </select>
      <input type="search" id="searchInput" placeholder="Введите запрос…" autocomplete="off">
      <button class="btn btn-primary" id="searchBtn">Поиск</button>
      <button class="btn" id="resetBtn">Сброс</button>
      <button class="btn" id="expandAll">Развернуть всё</button>
      <button class="btn" id="collapseAll">Свернуть всё</button>
      <span class="count" id="count"></span>
    </div>
  </div>
</header>

<main>
  <div id="list"></div>

  <div id="initialMessage">
    <div class="big"></div>
    <div class="msg">Выберите тип поиска и нажмите «Поиск»</div>
  </div>

  <div id="noResults">
    <div class="big"></div>
    <div class="msg" id="noResultsMsg">Такой задачи нет</div>
  </div>
</main>

<script>
const tasksData = __TASKS_JSON__;
const ALL_MODE = __ALL_MODE__;

const searchTypeEl = document.getElementById('searchType');
const searchInput  = document.getElementById('searchInput');
const searchBtn    = document.getElementById('searchBtn');
const resetBtn     = document.getElementById('resetBtn');
const countEl      = document.getElementById('count');
const noResults    = document.getElementById('noResults');
const noResMsg     = document.getElementById('noResultsMsg');
const listEl       = document.getElementById('list');
const initMsg      = document.getElementById('initialMessage');

const PLACEHOLDER = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
const MAX_CONCURRENT = 6;
let activeLoads = 0;
const loadQueue = [];

function pumpQueue() {
  while (activeLoads < MAX_CONCURRENT && loadQueue.length > 0) {
    const img = loadQueue.shift();
    if (!img.isConnected || !img.hasAttribute('data-src')) continue;
    activeLoads++;
    startLoad(img);
  }
}

function startLoad(img) {
  const url = img.getAttribute('data-src');
  const attempt = Number(img.getAttribute('data-attempt') || 0);
  img.onload = function () {
    img.removeAttribute('data-src');
    activeLoads--;
    pumpQueue();
  };
  img.onerror = function () {
    activeLoads--;
    if (attempt < 3) {
      img.setAttribute('data-attempt', String(attempt + 1));
      setTimeout(function () {
        loadQueue.unshift(img);
        pumpQueue();
      }, 400 * (attempt + 1));
    } else {
      img.removeAttribute('data-src');
    }
    pumpQueue();
  };
  img.src = url;
}

const lazyObserver = new IntersectionObserver(function (entries) {
  entries.forEach(function (entry) {
    if (entry.isIntersecting) {
      lazyObserver.unobserve(entry.target);
      loadQueue.push(entry.target);
      pumpQueue();
    }
  });
}, { rootMargin: '400px 0px' });

function observeImages(root) {
  root.querySelectorAll('img[data-src]').forEach(function (img) {
    lazyObserver.observe(img);
  });
}

tasksData.questions.forEach((task, idx) => {
  task._seq = String(idx + 1);
  task._id = String(task.id);
  task._ege = String(task.ege || '');
  
  let searchText = '';
  searchText += (task.name || '') + ' ';
  searchText += (task.theme_path || '') + ' ';
  searchText += (task.tags || []).join(' ') + ' ';
  searchText += (task.sources || []).join(' ') + ' ';
  
  const extractText = (html) => {
    if (!html) return '';
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || '';
  };
  
  searchText += extractText(task.question_html) + ' ';
  searchText += extractText(task.solution_html) + ' ';
  searchText += extractText(task.answer_html) + ' ';
  searchText += extractText(task.grade_criteria_html) + ' ';
  
  task._search = searchText.toLowerCase().replace(/\\s+/g, ' ');
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function rewriteImages(html, images) {
  if (!html) return '';
  const imgMap = {};
  for (const [fname, url] of Object.entries(images || {})) {
    imgMap[fname] = url;
  }
  return html.replace(/src=(["'])([^"']+)\\1/g, function (match, quote, src) {
    const fname = src.split('/').pop();
    const url = imgMap[fname] || (src.startsWith('http') ? src : '');
    if (!url) return match;
    return 'src=' + quote + PLACEHOLDER + quote +
           ' data-src=' + quote + url + quote +
           ' referrerpolicy="no-referrer"';
  });
}

function renderTask(task) {
  const tid = task.id;
  const name = escapeHtml(task.name || 'Без названия');
  const themePath = escapeHtml(task.theme_path || '');

  const tags = task.tags || [];
  const tagChips = tags.map(t => `<span class="chip">${escapeHtml(t)}</span>`).join('');
  
  const sources = task.sources || [];
  const srcChips = sources.map(s => `<span class="chip chip-src">${escapeHtml(s)}</span>`).join('');

  const qHtml = rewriteImages(task.question_html || '', task.images);
  const sHtml = rewriteImages(task.solution_html || '', task.images);
  const aHtml = rewriteImages(task.answer_html || '', task.images);
  const cHtml = rewriteImages(task.grade_criteria_html || '', task.images);

  function section(title, content, opened = false) {
    if (!content.trim()) return '';
    const openAttr = opened ? ' open' : '';
    return `
      <details class="section"${openAttr}>
        <summary>${title}</summary>
        <div class="tex-content">${content}</div>
      </details>
    `;
  }

  const sections = 
    section('Условие', qHtml, true) +
    section('Решение', sHtml) +
    section('Ответ', aHtml) +
    section('Критерии оценивания', cHtml);

  const egeBadge = (ALL_MODE && task._ege) ? `<span class="badge badge-ege">ЕГЭ №${task._ege}</span>` : '';

  return `
    <div class="task-card" data-seq="${task._seq}" data-id="${tid}">
      <div class="task-head">
        ${egeBadge}
        <span class="badge badge-num">№${task._seq}</span>
        <span class="badge badge-id">ID ${tid}</span>
        <span class="task-name">${name}</span>
      </div>
      ${themePath ? `<div class="theme-path">${themePath}</div>` : ''}
      <div class="task-meta">
        ${tagChips ? `<div class="chips">${tagChips}</div>` : ''}
        ${srcChips ? `<div class="chips">${srcChips}</div>` : ''}
      </div>
      ${sections}
    </div>
  `;
}

function updatePlaceholder() {
  const t = searchTypeEl.value;
  if (t === 'number') {
    searchInput.placeholder = 'Номер задачи (№ или ID)';
  } else if (t === 'ege') {
    searchInput.placeholder = 'Номер задания ЕГЭ (1-26)';
  } else {
    searchInput.placeholder = 'Текст для поиска…';
  }
}

function doSearch() {
  const type  = searchTypeEl.value;
  const query = searchInput.value.trim();

  if (!query) {
    listEl.innerHTML = '';
    initMsg.style.display = 'block';
    noResults.style.display = 'none';
    countEl.textContent = '';
    return;
  }

  initMsg.style.display = 'none';

  const filtered = tasksData.questions.filter(task => {
    if (type === 'number') {
      return (task._seq === query) || (task._id === query) ||
             task._id.startsWith(query) || task._seq.startsWith(query);
    }
    if (type === 'ege') {
      return task._ege === query;
    }
    return task._search.includes(query.toLowerCase());
  });

  if (filtered.length === 0) {
    listEl.innerHTML = '';
    noResults.style.display = 'block';
    if (type === 'number') {
      noResMsg.textContent = `Задачи с номером «${query}» нет`;
    } else if (type === 'ege') {
      noResMsg.textContent = `Задачи ЕГЭ №${query} не найдены`;
    } else {
      noResMsg.textContent = `По запросу «${query}» ничего не найдено`;
    }
    countEl.textContent = `Показано 0 из ${tasksData.questions.length}`;
  } else {
    noResults.style.display = 'none';
    listEl.innerHTML = filtered.map(renderTask).join('');
    observeImages(listEl);
    countEl.textContent = `Показано ${filtered.length} из ${tasksData.questions.length}`;
  }
}

function doReset() {
  searchInput.value = '';
  listEl.innerHTML = '';
  initMsg.style.display = 'block';
  noResults.style.display = 'none';
  countEl.textContent = '';
  searchInput.focus();
}

searchTypeEl.addEventListener('change', updatePlaceholder);
searchBtn.addEventListener('click', doSearch);
resetBtn.addEventListener('click', doReset);

searchInput.addEventListener('keydown', function (e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    doSearch();
  }
});

document.getElementById('expandAll').addEventListener('click', () => {
  document.querySelectorAll('details.section').forEach(d => d.open = true);
});

document.getElementById('collapseAll').addEventListener('click', () => {
  document.querySelectorAll('details.section').forEach(d => d.open = false);
});

updatePlaceholder();
initMsg.style.display = 'block';
noResults.style.display = 'none';
</script>
</body>
</html>
"""

def build_page(questions, page_title, h1, options_html, all_mode) -> str:
    tasks_json_str = json.dumps({"questions": questions}, ensure_ascii=False, indent=None)
    return (
        PAGE_TEMPLATE
        .replace("__PAGE_TITLE__", page_title)
        .replace("__H1__", h1)
        .replace("__TOTAL__", str(len(questions)))
        .replace("__SEARCH_OPTIONS__", options_html)
        .replace("__ALL_MODE__", "true" if all_mode else "false")
        .replace("__TASKS_JSON__", tasks_json_str)
    )

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Генерация самодостаточного HTML-просмотрщика задач ЕГЭ"
    )
    parser.add_argument("task", type=str,
                        help="Номер задачи ЕГЭ (1-26) или all для общего файла")
    parser.add_argument("--json", type=str, default="",
                        help="Путь к JSON (по умолчанию tasks_{n}.json)")
    parser.add_argument("--out", type=str, default="",
                        help="Путь к выходному HTML (по умолчанию tasks_{n}.html или tasks_all.html)")
    parser.add_argument("--open", action="store_true",
                        help="Открыть результат в браузере")
    args = parser.parse_args()

    if args.task.lower() == "all":
        merged = []
        found = []
        for n in range(1, 27):
            p = Path(f"tasks_{n}.json")
            if not p.exists():
                continue
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            qs = data.get("questions") or []
            for q in qs:
                q["ege"] = n
            merged.extend(qs)
            found.append(n)
        if not merged:
            sys.exit("Не найдено ни одного файла tasks_{n}.json (1-26)")
        print(f"Найдено файлов: {len(found)} ({', '.join(map(str, found))})")
        print(f"Всего задач: {len(merged)}")
        page = build_page(merged, "Задачи ЕГЭ 1-26 — Физика", "Задачи ЕГЭ 1-26",
                          ALL_OPTIONS, True)
        out_path = Path(args.out) if args.out else Path("tasks_all.html")
    else:
        try:
            n = int(args.task)
        except ValueError:
            parser.error("Ожидался номер задачи (1-26) или all")
        if not 1 <= n <= 26:
            parser.error("Номер задачи должен быть от 1 до 26")
        json_path = Path(args.json) if args.json else Path(f"tasks_{n}.json")
        if not json_path.exists():
            sys.exit(f"Файл не найден: {json_path}\n"
                     f"   Сначала скачайте задачи:  python3 shkolkovo_task_loader.py {n}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tasks = data.get("questions") or []
        if not tasks:
            sys.exit("В JSON нет ни одной задачи.")
        print(f"Всего задач: {len(tasks)}")
        page = build_page(tasks, f"Задачи ЕГЭ №{n} — Физика", f"Задачи ЕГЭ №{n}",
                          SINGLE_OPTIONS, False)
        out_path = Path(args.out) if args.out else Path(f"tasks_{n}.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    file_size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\nГотово: {out_path}")
    print(f"   Размер файла: {file_size_mb:.1f} МБ")
    if file_size_mb > 50:
        print("   Файл большой, браузер может открывать его несколько секунд")
    print("   Файл самодостаточный — можно отправлять по почте/мессенджерам")

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())

if __name__ == "__main__":
    main()
  