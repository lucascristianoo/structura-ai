/**
 * Structura.AI — Project Dossier Markdown Sanitizer & Renderer
 * Extracted from project_view.html for clean frontend organization.
 */

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('ai-review-content');
  if (!container || !window.marked || !window.DOMPurify) return;

  const rawMarkdown = container.textContent.trim();
  if (!rawMarkdown) return;

  const rawHtml = window.marked.parse(rawMarkdown, { gfm: true, breaks: true });
  container.innerHTML = window.DOMPurify.sanitize(rawHtml);
  container.classList.remove('whitespace-pre-wrap');
});

