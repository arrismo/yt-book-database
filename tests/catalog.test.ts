import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import { searchBooks, timecode, videoLink, type Catalog } from "../lib/catalog.ts";
const catalog=JSON.parse(readFileSync(new URL("../data/catalog.json",import.meta.url),"utf8")) as Catalog;

test("search covers author, title, transcript evidence and video titles",()=>{
  assert.equal(searchBooks(catalog,"Baradaran","All subjects","all",false,[],"title")[0]?.id,"color-of-money");
  assert.ok(searchBooks(catalog,"stealing empire","All subjects","all",false,[],"title").some(b=>b.id==="stealing-empire"));
  assert.ok(searchBooks(catalog,"15th anniversary","All subjects","all",false,[],"title").some(b=>b.id==="mixtape-manifesto"));
});
test("subject, evidence, and shelf filters intersect",()=>{
  assert.equal(searchBooks(catalog,"","Economics","all",false,[],"title").length,2);
  assert.equal(searchBooks(catalog,"","Media & culture","notes",false,[],"title")[0]?.id,"mixtape-manifesto");
  assert.deepEqual(searchBooks(catalog,"","All subjects","all",true,["color-of-money"],"title").map(b=>b.id),["color-of-money"]);
  assert.equal(searchBooks(catalog,"unfindablexyz","All subjects","all",false,[],"title").length,0);
});
test("all records have reviewed source evidence and valid deep links",()=>{
  for(const b of catalog.books)assert.ok(catalog.mentions.some(m=>m.book_id===b.id));
  for(const m of catalog.mentions){const v=catalog.videos.find(v=>v.video_id===m.video_id)!;assert.ok(v);assert.equal(m.review_status,"confirmed");const link=videoLink(v,m);assert.ok(link.startsWith("https://www.youtube.com/watch?v="));if(m.start_seconds===null)assert.ok(!link.includes("&t="));else assert.ok(link.endsWith(`&t=${Math.floor(m.start_seconds)}s`));}
});
test("timestamps support hours and never round ahead of a passage",()=>{
  assert.equal(timecode(18809.36),"5:13:29");assert.equal(timecode(75.96),"1:15");assert.equal(timecode(0),"0:00");
});
test("sort results do not mutate the source catalog",()=>{
  const before=JSON.stringify(catalog.books);const sorted=searchBooks(catalog,"","All subjects","all",false,[],"mentions");assert.equal(sorted[0].id,"mixtape-manifesto");assert.equal(JSON.stringify(catalog.books),before);
});
test("the pilot and displayed counts are internally consistent",()=>{
  assert.equal(catalog.coverage.pilot_sample.length,10);assert.equal(catalog.videos.length,10);assert.equal(catalog.books.length,11);assert.equal(catalog.mentions.length,14);assert.ok(catalog.videos.every(v=>v.transcript.status==="available"));
});
