import catalog from "../data/catalog.json";

export type CaptionSegment = {
  text: string;
  start_seconds: number;
};

export type CaptionBookMatch = {
  book_id: string;
  title: string;
  author: string;
  subject: string;
  start_seconds: number;
  evidence_excerpt: string;
};

function normalize(value: string): string {
  return value.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
}

function hasTitle(text: string, title: string): boolean {
  const haystack = ` ${normalize(text)} `;
  const needle = ` ${normalize(title)} `;
  return haystack.includes(needle);
}

export function matchCaptionSegments(segments: CaptionSegment[]): CaptionBookMatch[] {
  const safeSegments = segments
    .filter((segment) => typeof segment?.text === "string" && segment.text.trim() && Number.isFinite(segment.start_seconds))
    .slice(-8);
  const matches: CaptionBookMatch[] = [];

  for (let index = 0; index < safeSegments.length; index += 1) {
    const window = safeSegments.slice(index, index + 4);
    const excerpt = window.map((segment) => segment.text.trim()).join(" ").slice(0, 500);
    for (const book of catalog.books) {
      if (matches.some((match) => match.book_id === book.id) || !hasTitle(excerpt, book.title)) continue;
      matches.push({
        book_id: book.id,
        title: book.title,
        author: book.author,
        subject: book.subject,
        start_seconds: window[0].start_seconds,
        evidence_excerpt: excerpt,
      });
    }
  }

  return matches;
}
