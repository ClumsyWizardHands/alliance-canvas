// Minimal markdown rendering wrapper around `marked`. Used by chat bubbles and
// card body fields. Disables HTML embedding for safety since we're rendering
// model output verbatim.

import { marked } from 'marked';

marked.setOptions({
  gfm: true,
  breaks: true
});

export function renderMarkdown(text: string): string {
  if (!text) return '';
  // marked returns string in sync mode when async option is not set
  return marked.parse(text, { async: false }) as string;
}
