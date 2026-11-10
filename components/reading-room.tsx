"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDownToLine, ArrowRight, ArrowUpRight, Bookmark, BookOpen, Check, CheckCheck, ChevronRight, CircleHelp, ExternalLink, FileText, Grid2X2, Library, List, LockKeyhole, Menu, Play, Search, SlidersHorizontal, Video as VideoIcon, X } from "lucide-react";
import { Book, Catalog, channelLink, searchBooks, timecode, videoLink } from "@/lib/catalog";

const SHELF_KEY = "reading-room-shelf-v1";
// Read the previous storage key once so existing reading shelves survive the rename.
const LEGACY_SHELF_KEY = "jared-reading-room-shelf-v1";
const date = (value: string) => new Date(value.slice(0,10)+"T12:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"});

function Cover({book,large=false}:{book:Book;large?:boolean}) {
  const [failed,setFailed]=useState(false);
  return <div className={`cover ${large?"large":""} tone-${book.id.length%4}`}>
    {book.cover_url&&!failed ? <img src={book.cover_url} alt={`${book.title} book cover`} onError={()=>setFailed(true)} loading="lazy"/> : <div className="type-cover"><span>READING ROOM EDITION</span><strong>{book.title}</strong><small>{book.author}</small><BookOpen size={28}/></div>}
  </div>;
}

export default function ReadingRoom({catalog}:{catalog:Catalog}) {
  const [view,setView]=useState("all");
  const [query,setQuery]=useState("");
  const [subject,setSubject]=useState("All subjects");
  const [evidence,setEvidence]=useState("all");
  const [sort,setSort]=useState("title");
  const [layout,setLayout]=useState("grid");
  const [saved,setSaved]=useState<string[]>([]);
  const [selected,setSelected]=useState<string|null>(null);
  const [mobile,setMobile]=useState(false);
  const [toast,setToast]=useState("");
  const searchRef=useRef<HTMLInputElement>(null);
  const dialogRef=useRef<HTMLDialogElement>(null);
  const subjects=Array.from(new Set(catalog.books.map(b=>b.subject))).sort();
  const results=searchBooks(catalog,query,subject,evidence,view==="saved",saved,sort);
  const book=catalog.books.find(b=>b.id===selected);
  const available=catalog.videos.filter(v=>v.transcript.status==="available").length;

  useEffect(()=>{
    try { const s=JSON.parse(localStorage.getItem(SHELF_KEY)??localStorage.getItem(LEGACY_SHELF_KEY)??"[]");if(Array.isArray(s)){const ids=s.filter((id)=>typeof id==="string"&&catalog.books.some(b=>b.id===id));setSaved(ids);localStorage.setItem(SHELF_KEY,JSON.stringify(ids));} } catch {}
    const read=()=>setSelected(new URLSearchParams(location.search).get("book"));
    read();window.addEventListener("popstate",read);
    const shortcut=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key==="k"){e.preventDefault();searchRef.current?.focus();}};
    window.addEventListener("keydown",shortcut);
    return ()=>{window.removeEventListener("popstate",read);window.removeEventListener("keydown",shortcut);};
  },[catalog.books]);
  useEffect(()=>{
    if(book&&!dialogRef.current?.open)dialogRef.current?.showModal();
    if(!book&&dialogRef.current?.open)dialogRef.current?.close();
  },[book]);
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(""),3000);return()=>clearTimeout(t);},[toast]);

  function toggleSaved(id:string) {
    const next=saved.includes(id)?saved.filter(s=>s!==id):[...saved,id];setSaved(next);
    try{localStorage.setItem(SHELF_KEY,JSON.stringify(next));setToast(next.includes(id)?"Added to your reading shelf":"Removed from your reading shelf");}catch{setToast("Saved for this session. Browser storage is unavailable.");}
  }
  function openBook(id:string) {
    setSelected(id);const u=new URL(location.href);u.searchParams.set("book",id);history.pushState(null,"",u);
  }
  function closeBook() {
    setSelected(null);const u=new URL(location.href);u.searchParams.delete("book");history.replaceState(null,"",u);
  }
  function navigate(next:string) {setView(next);setMobile(false);setQuery("");setSubject("All subjects");setEvidence("all");}
  function reset() {setQuery("");setSubject("All subjects");setEvidence("all");}
  async function copyLink() {
    try {await navigator.clipboard.writeText(location.href);setToast("Book link copied");} catch {setToast("Copy the book URL from your address bar");}
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to collection</a>
    {mobile&&<button className="nav-backdrop" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
    <aside className={`sidebar ${mobile?"visible":""}`}>
      <button className="brand" onClick={()=>navigate("all")} aria-label="Reading Room home"><span className="brand-mark"><Library size={23} strokeWidth={1.5}/></span><span>Reading<br/>Room<span className="brand-dot">.</span></span></button>
      <div className="sidebar-label">YOUR YOUTUBE BOOK ARCHIVE</div>
      <nav aria-label="Main navigation" className="main-nav">
        <button className={view==="all"?"active":""} onClick={()=>navigate("all")}><BookOpen size={18}/>All books<span className="nav-count">{catalog.books.length}</span></button>
        <button className={view==="saved"?"active":""} onClick={()=>navigate("saved")}><Bookmark size={18}/>My reading shelf<span className="nav-count">{saved.length}</span></button>
        <button className={view==="sources"?"active":""} onClick={()=>navigate("sources")}><VideoIcon size={18}/>Sources & coverage</button>
      </nav>
      <div className="sidebar-label subject-label">EXPLORE BY SUBJECT</div>
      <nav aria-label="Book subjects" className="subject-nav">{subjects.map(s=><button key={s} className={subject===s&&(view==="all"||view==="saved")?"selected":""} onClick={()=>{setView("all");setSubject(s);setMobile(false);setQuery("");}}><span className={`subject-dot ${s.split(" ")[0].toLowerCase()}`}/>{s}<span>{catalog.books.filter(b=>b.subject===s).length}</span></button>)}</nav>
      <div className="sidebar-bottom"><button className={`about-link ${view==="about"?"selected":""}`} onClick={()=>navigate("about")}><CircleHelp size={17}/>About this archive<ArrowUpRight size={14}/></button><div className="privacy"><LockKeyhole size={12}/>Your private research space</div></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu size={22}/></button><div className="breadcrumb">THE ARCHIVE <ChevronRight size={12}/><span>{view==="saved"?"Reading shelf":view==="sources"?"Sources & coverage":view==="about"?"About":"Collection"}</span></div><div className="topbar-right"><button className="source-nav-link" onClick={()=>navigate("sources")}>Browse sources<ArrowUpRight size={14}/></button><span className="avatar" title="Personal archive">M</span></div></header>
      <main id="main-content" className="content">
        {(view==="all"||view==="saved")&&<>
          {view==="saved"&&<section className="simple-intro"><div className="eyebrow">YOUR PERSONAL COLLECTION</div><h1>My reading shelf<span className="heading-dot">.</span></h1><p>Keep the books you want to come back to. Saved in this browser.</p></section>}
          <section className="collection" aria-label="Book collection">
            <div className="collection-heading"><h2>{view==="saved"?"Saved for later":"The collection"}<span>{view==="saved"?saved.length:catalog.books.length}</span></h2><a className="text-action" href="/catalog.json" download="reading-room-catalog.json"><ArrowDownToLine size={15}/>Export catalog</a></div>
            <div className="search-row"><div className="search-field"><Search size={19}/><input ref={searchRef} aria-label="Search books, authors, or evidence" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search books, authors, or a phrase from the conversation…"/>{query?<button aria-label="Clear search" onClick={()=>setQuery("")}><X size={16}/></button>:<kbd>⌘ K</kbd>}</div></div>
            <div className="filters"><div className="filter-select"><SlidersHorizontal size={14}/><select aria-label="Filter by subject" value={subject} onChange={e=>setSubject(e.target.value)}><option>All subjects</option>{subjects.map(s=><option key={s}>{s}</option>)}</select></div><select aria-label="Filter by evidence" value={evidence} onChange={e=>setEvidence(e.target.value)}><option value="all">All evidence</option><option value="transcript">Transcript excerpts</option><option value="notes">Titles & show notes</option></select><div className="filter-spacer"/><label className="sort-label">Sort by <select aria-label="Sort books" value={sort} onChange={e=>setSort(e.target.value)}><option value="title">Title A–Z</option><option value="author">Author A–Z</option><option value="year">Publication year</option><option value="mentions">Source count</option></select></label><div className="view-switch"><button className={layout==="grid"?"active":""} onClick={()=>setLayout("grid")} aria-label="Grid view" aria-pressed={layout==="grid"}><Grid2X2 size={16}/></button><button className={layout==="list"?"active":""} onClick={()=>setLayout("list")} aria-label="List view" aria-pressed={layout==="list"}><List size={18}/></button></div></div>
            <div className="results-meta" aria-live="polite"><span>{results.length} {results.length===1?"book":"books"}{subject!=="All subjects"?` in ${subject}`:""}{query?` matching “${query}”`:""}</span>{(query||subject!=="All subjects"||evidence!=="all")&&<button onClick={reset}>Clear filters<X size={12}/></button>}<span className="review-legend"><span/>Source evidence reviewed</span></div>
            {results.length?<div className={`book-grid ${layout==="list"?"list-layout":""}`}>{results.map((b,index)=>{const mentions=catalog.mentions.filter(m=>m.book_id===b.id);return <article className="book-card" key={b.id} style={{animationDelay:`${Math.min(index,5)*35}ms`}}><button className="book-open" onClick={()=>openBook(b.id)} aria-label={`Open ${b.title}`}><div className="book-stage"><Cover book={b}/><span className="open-hint">View record <ArrowUpRight size={14}/></span></div><div className="book-copy"><div className="book-category">{b.subject}</div><h3>{b.title}</h3><p>{b.author}</p>{layout==="list"&&<span className="list-description">{b.description}</span>}</div></button><div className="card-footer"><span><VideoIcon size={13}/>{mentions.length} source {mentions.length===1?"reference":"references"}</span><button className={`save-button ${saved.includes(b.id)?"is-saved":""}`} onClick={()=>toggleSaved(b.id)} aria-label={`${saved.includes(b.id)?"Remove":"Save"} ${b.title}${saved.includes(b.id)?" from":" to"} reading shelf`} aria-pressed={saved.includes(b.id)}><Bookmark size={17} fill={saved.includes(b.id)?"currentColor":"none"}/></button></div></article>})}</div>:<div className="empty-state"><BookOpen size={34} strokeWidth={1}/><h3>{view==="saved"&&!saved.length?"Your next read starts here.":"No books found."}</h3><p>{view==="saved"&&!saved.length?"Use the bookmark on any book to add it to your reading shelf.":"Try another title, author, or subject."}</p><button className="primary-button" onClick={()=>view==="saved"&&!saved.length?navigate("all"):reset()}>{view==="saved"&&!saved.length?"Explore the collection":"Clear search & filters"}<ArrowRight size={15}/></button></div>}
          </section>
          <div className="coverage-strip"><FileText size={19}/><div><b>A collection with a paper trail.</b><p>{available} of {catalog.videos.length} pilot transcripts retrieved. Full channel inventories have not been run.</p></div><button onClick={()=>navigate("sources")}>See coverage<ArrowRight size={15}/></button></div>
        </>}
        {view==="sources"&&<><section className="simple-intro"><div className="eyebrow">THE EVIDENCE BEHIND THE BOOKS</div><h1>Sources & coverage<span className="heading-dot">.</span></h1><p>See what was checked, where each record came from, and what’s still missing.</p></section><div className="coverage-stats"><div><strong>{catalog.videos.length}</strong><span>videos in the pilot</span></div><div><strong>{available}/{catalog.videos.length}</strong><span>transcripts retrieved</span></div><div><strong>{catalog.mentions.length}</strong><span>reviewed references</span></div></div><div className="scope-note"><CircleHelp size={19}/><div><b>Starter collection · full-channel inventory pending</b><p>{catalog.coverage.notice}</p></div></div><div className="source-heading"><h2>Source videos</h2><span>Checked {date(catalog.coverage.as_of)}</span></div><div className="search-field source-search"><Search size={18}/><input aria-label="Search source videos" placeholder="Search source video titles…" value={query} onChange={e=>setQuery(e.target.value)}/></div><div className="source-list">{catalog.videos.filter(v=>v.title.toLowerCase().includes(query.toLowerCase())).map(v=><article className="source-row" key={v.video_id}><div className="source-play"><VideoIcon size={20}/></div><div className="source-copy"><a href={v.url} target="_blank" rel="noreferrer">{v.title}<ArrowUpRight size={15}/></a><p><a href={channelLink(v)} target="_blank" rel="noreferrer">Source channel</a> <span>·</span> {catalog.mentions.filter(m=>m.video_id===v.video_id).length} reviewed {catalog.mentions.filter(m=>m.video_id===v.video_id).length===1?"reference":"references"}</p></div><span className={`status-tag ${v.transcript.status==="available"?"good":""}`}>{v.transcript.status==="available"?<Check size={12}/>:null}{v.transcript.status==="available"?"Transcript retrieved":v.transcript.status.replaceAll("_"," ")}</span><a href={v.url} target="_blank" rel="noreferrer" className="icon-button source-out" aria-label={`Open source video: ${v.title}`}><ExternalLink size={17}/></a></article>)}</div>{!catalog.videos.some(v=>v.title.toLowerCase().includes(query.toLowerCase()))&&<p className="no-sources">No source videos match your search.</p>}<div className="method-note"><h3>How a reference becomes a record</h3><p>Accessible captions → exact title matching → manual context review → a short excerpt and source link. A retrieved transcript can have no confirmed book records yet. Caption text may contain errors; timestamps point to the original segment.</p><p>Short titles, names, jingles, and ambiguous phrases are reviewed before inclusion. Mentioning a book does not imply endorsement.</p></div></>}
        {view==="about"&&<><section className="simple-intro"><div className="eyebrow">CONTEXT, NOT RECOMMENDATIONS</div><h1>A trail of ideas<span className="heading-dot">.</span></h1><p>A personal research companion to the conversations on your favorite YouTube channels.</p></section><div className="about-grid"><section className="about-card"><BookOpen size={24}/><h2>Read with the source.</h2><p>This archive collects explicitly named books and connects them to the videos where they appear. Open a book to see its evidence, context, and source links.</p><p>“Discussed” and “referenced” describe the available context. A mention does not imply a recommendation.</p></section><section className="about-card"><CheckCheck size={24}/><h2>Small, and verifiable.</h2><p>The first collection contains {catalog.books.length} books and {catalog.mentions.length} reviewed references across {catalog.videos.length} selected videos. It is not a complete inventory of any channel.</p><p>Some records use video titles or show notes instead of a timed passage. These are labeled separately. Missing dates are left blank.</p></section><section className="about-card"><FileText size={24}/><h2>A straightforward workflow.</h2><p>Book data lives in SQLite. Accessible captions are checked with deterministic title matching and manual review. This site serves a catalog exported from that database.</p><p>No Supabase, model-based extraction, embeddings, or generated quotations. The full-channel inventory command uses the official YouTube Data API and needs a local API key.</p></section><section className="about-card"><LockKeyhole size={24}/><h2>Your research space.</h2><p>This site is hosted with owner-only access. Your reading shelf is saved in this browser and does not sync between devices. Clearing browser data clears the shelf.</p><p>This is an independent personal archive and is not affiliated with or endorsed by any featured creator or author.</p></section></div><button className="primary-button" onClick={()=>navigate("all")}>Back to the collection<ArrowRight size={15}/></button></>}
        <footer className="site-footer"><span>READING ROOM<span className="footer-dot">.</span> <span className="footer-byline">Your YouTube book archive</span></span><span>Every mention has a source. A mention is not an endorsement.</span></footer>
      </main>
    </div>
    <dialog ref={dialogRef} className="book-dialog" onCancel={e=>{e.preventDefault();closeBook();}} onClick={e=>{if(e.target===e.currentTarget)closeBook();}} aria-labelledby="record-title">
      {book&&<div className="record"><div className="record-top"><span className="tiny-caps">BOOK RECORD</span><button className="icon-button" aria-label="Close book record" onClick={closeBook}><X size={21}/></button></div><div className="record-layout"><aside className="record-aside"><div className="record-cover"><Cover book={book} large/></div><button className={`primary-button shelf-button ${saved.includes(book.id)?"saved":""}`} onClick={()=>toggleSaved(book.id)}>{saved.includes(book.id)?<Check size={15}/>:<Bookmark size={15}/>} {saved.includes(book.id)?"On your reading shelf":"Save to reading shelf"}</button><button className="secondary-button" onClick={copyLink}>Copy record link<ArrowUpRight size={14}/></button><div className="record-metadata"><span>AUTHOR / EDITOR</span><p>{book.author}</p>{book.year&&<><span>FIRST PUBLISHED</span><p>{book.year}</p></>}<span>SUBJECT</span><p>{book.subject}</p>{book.isbn&&<><span>CATALOG ISBN</span><p>{book.isbn}</p></>}{book.open_library_id&&<a href={`https://openlibrary.org${book.open_library_id}`} target="_blank" rel="noreferrer">View catalog entry<ArrowUpRight size={13}/></a>}</div></aside><section className="record-content"><div className="book-category">{book.subject}</div><h2 id="record-title">{book.title}</h2><p className="record-author">{book.author}</p><p className="record-description">{book.description}</p><div className="evidence-heading"><h3>In the conversation</h3><span>{catalog.mentions.filter(m=>m.book_id===book.id).length} sources</span></div>{catalog.mentions.filter(m=>m.book_id===book.id).map(m=>{const v=catalog.videos.find(v=>v.video_id===m.video_id)!;return <article className="evidence-card" key={m.id}><div className="evidence-label"><span>{m.evidence_type==="transcript"?<FileText size={13}/>:<VideoIcon size={13}/>} {m.evidence_type==="transcript"?"TRANSCRIPT EXCERPT":m.evidence_type==="video_title"?"VIDEO TITLE":"SOURCE SHOW NOTES"}</span><span className="context-tag">{m.classification}</span></div><blockquote>“{m.evidence_excerpt}”</blockquote><p className="evidence-note">{m.note}</p><a href={videoLink(v,m)} target="_blank" rel="noreferrer" className="video-title">{v.title}<ArrowUpRight size={14}/></a><div className="evidence-actions"><a href={videoLink(v,m)} target="_blank" rel="noreferrer" className="watch-link"><Play size={12} fill="currentColor"/>{m.start_seconds===null?"Open video":`Watch at ${timecode(m.start_seconds)}`}</a>{v.source_url&&<a href={v.source_url} target="_blank" rel="noreferrer">Source page<ArrowUpRight size={12}/></a>}</div>{m.evidence_type==="transcript"?<div className="caption-note">YouTube captions · may contain transcription errors</div>:<div className="caption-note">No precise transcript passage assigned to this reference</div>}</article>})}<p className="record-footnote"><CheckCheck size={14}/>Evidence reviewed in context. A mention is not an endorsement.</p></section></div></div>}
    </dialog>
    {toast&&<div className="toast" role="status"><Check size={16}/>{toast}</div>}
  </div>;
}
