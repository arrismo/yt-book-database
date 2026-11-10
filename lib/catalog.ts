export type Book = {
  id: string; title: string; author: string; year: number | null;
  subject: string; isbn: string | null; open_library_id: string | null;
  cover_url: string | null; description: string; verified_at: string | null;
};
export type Video = {
  video_id: string; title: string; channel_id: string; url: string;
  published_at: string | null; source_url: string | null; source_date: string | null;
  transcript: { status: string; provider?: string; attempted_at?: string; error_code?: string | null };
};
export type Mention = {
  id: string; book_id: string; video_id: string; start_seconds: number | null;
  evidence_excerpt: string; evidence_type: string; classification: string;
  confidence: number | null; review_status: string; extraction_method: string; note: string | null;
};
export type Catalog = {
  books: Book[]; videos: Video[]; mentions: Mention[];
  coverage: { as_of: string; scope: string; inventory: unknown; pilot_sample: string[]; segments_processed: number; notice: string };
};
export function normalize(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}
export function timecode(seconds: number) {
  const n = Math.floor(seconds), h = Math.floor(n / 3600), m = Math.floor((n % 3600) / 60), s = n % 60;
  return h ? `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}` : `${m}:${String(s).padStart(2,"0")}`;
}
export function videoLink(video: Video, mention: Mention) {
  return video.url + (mention.start_seconds === null ? "" : `&t=${Math.floor(mention.start_seconds)}s`);
}
export function searchBooks(catalog: Catalog, query: string, subject: string, evidence: string, savedOnly: boolean, saved: string[], sort: string) {
  const terms = normalize(query.trim()).split(/\s+/).filter(Boolean);
  const result = catalog.books.filter(b => {
    const mentions = catalog.mentions.filter(m => m.book_id === b.id);
    const text = normalize([b.title,b.author,b.subject,...mentions.map(m=>m.evidence_excerpt),...mentions.map(m=>catalog.videos.find(v=>v.video_id===m.video_id)?.title||"")].join(" "));
    return terms.every(t=>text.includes(t)) && (subject === "All subjects" || b.subject === subject) &&
      (evidence !== "transcript" || mentions.some(m=>m.evidence_type === "transcript")) &&
      (evidence !== "notes" || mentions.some(m=>m.evidence_type !== "transcript")) &&
      (!savedOnly || saved.includes(b.id));
  });
  const count=(b:Book)=>catalog.mentions.filter(m=>m.book_id===b.id).length;
  return result.sort((a,b)=>sort==="author"?a.author.localeCompare(b.author):sort==="year"?(b.year||0)-(a.year||0):sort==="mentions"?count(b)-count(a)||a.title.localeCompare(b.title):a.title.localeCompare(b.title));
}
