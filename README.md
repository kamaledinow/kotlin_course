# Resume Builder (Editor.js)

Минималистичный билдер резюме с блоковым редактором на базе **Editor.js** и экспортом в **PDF**.

## Возможности MVP
- блоковый редактор (Header / Paragraph / List);
- live preview резюме справа;
- экспорт данных в `resume.json`;
- загрузка демо-профиля;
- экспорт в PDF (A4).

## Запуск
```bash
npm ci
npm start
```

Приложение будет доступно на `http://localhost:8080`.

## Технологии
- Editor.js (CDN)
- html2pdf.js (CDN)
- Vanilla JS + CSS

## Дальше по roadmap
- отдельные resume-блоки (Experience / Education / Skills) с валидацией;
- несколько шаблонов оформления;
- multi-page export без разрыва блоков;
- сохранение в LocalStorage и облачный бэкенд.
