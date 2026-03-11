const demoData = {
  time: Date.now(),
  blocks: [
    {
      type: 'header',
      data: {
        text: 'Алексей Иванов',
        level: 1,
      },
    },
    {
      type: 'paragraph',
      data: {
        text: 'Product Designer · alex@example.com · +7 (900) 000-00-00 · Moscow',
      },
    },
    {
      type: 'header',
      data: {
        text: 'Summary',
        level: 2,
      },
    },
    {
      type: 'paragraph',
      data: {
        text: 'Дизайнер с 7+ годами опыта в B2C-продуктах. Проектирую интерфейсы с фокусом на типографику, иерархию и метрики.',
      },
    },
    {
      type: 'header',
      data: {
        text: 'Experience',
        level: 2,
      },
    },
    {
      type: 'list',
      data: {
        style: 'unordered',
        items: [
          'Senior Product Designer — FinTech, 2021–2025',
          'Product Designer — EdTech, 2018–2021',
          'UI Designer — Agency, 2016–2018',
        ],
      },
    },
    {
      type: 'header',
      data: {
        text: 'Skills',
        level: 2,
      },
    },
    {
      type: 'paragraph',
      data: {
        text: 'Figma, Design Systems, UX Research, HTML/CSS, Prototyping, Product Analytics',
      },
    },
  ],
};

const editor = new EditorJS({
  holder: 'editorjs',
  placeholder: 'Введите содержимое резюме...',
  data: demoData,
  tools: {
    header: Header,
    list: List,
  },
  async onChange() {
    const output = await editor.save();
    renderResume(output);
  },
});

function escapeHtml(value) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return value.replace(/[&<>"']/g, m => map[m]);
}

function renderResume(data) {
  const preview = document.getElementById('resume-preview');
  const html = data.blocks
    .map(block => {
      if (block.type === 'header') {
        const level = Math.min(Math.max(block.data.level, 1), 3);
        return `<h${level}>${escapeHtml(block.data.text)}</h${level}>`;
      }
      if (block.type === 'paragraph') {
        return `<p class="lead">${escapeHtml(block.data.text)}</p>`;
      }
      if (block.type === 'list') {
        const items = block.data.items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
        return `<ul>${items}</ul>`;
      }
      return '';
    })
    .join('');

  preview.innerHTML = html;
}

async function saveJson() {
  const content = await editor.save();
  const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'resume.json';
  a.click();
  URL.revokeObjectURL(url);
}

async function exportPdf() {
  const element = document.getElementById('resume-preview');
  const options = {
    margin: [8, 8, 8, 8],
    filename: 'resume.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  };
  await html2pdf().set(options).from(element).save();
}

async function loadDemo() {
  await editor.render(demoData);
  renderResume(demoData);
}

document.getElementById('save-json').addEventListener('click', saveJson);
document.getElementById('export-pdf').addEventListener('click', exportPdf);
document.getElementById('load-demo').addEventListener('click', loadDemo);

editor.isReady.then(async () => {
  const output = await editor.save();
  renderResume(output);
});
