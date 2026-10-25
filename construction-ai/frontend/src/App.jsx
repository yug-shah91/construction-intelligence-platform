import { useState, useEffect } from "react";
const inr = n => n >= 1e7 ? `₹${(n / 1e7).toFixed(2)} Cr` : `₹${(n / 1e5).toFixed(2)} L`;
async function api(path, opts) {
  const r = await fetch(path, opts);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || "Request failed");
  return j;
}
const Stat = ({ v, l }) => <div className="stat"><b>{v}</b><span>{l}</span></div>;

function ImageTool({ endpoint, render }) {
  const [file, setFile] = useState(null), [res, setRes] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true); setErr(""); setRes(null);
    try { const fd = new FormData(); fd.append("file", file); setRes(await api(endpoint, { method: "POST", body: fd })); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  return <div>
    <label htmlFor={endpoint}>Site photo (JPG, PNG or WEBP)</label>
    <input id={endpoint} type="file" accept="image/jpeg,image/png,image/webp" onChange={e => { setFile(e.target.files[0]); setRes(null); }} />
    {file && <img className="pv" src={URL.createObjectURL(file)} alt="Preview of uploaded site" />}
    <button className="go" disabled={!file || busy} onClick={run}>{busy ? "Analysing…" : "Analyse photo"}</button>
    {err && <p className="err" role="alert">{err}</p>}
    {res && <>{res.demo && <p className="note">Demo result. Add an API key on the server for real analysis.</p>}{render(res)}</>}
  </div>;
}

const Safety = () => <ImageTool endpoint="/api/safety" render={r => <>
  <div className="grid"><Stat v={r.safety_score} l="Safety score / 100" /><div className="stat"><span className={`pill ${r.overall_status}`}>{r.overall_status}</span></div></div>
  <p>{r.summary}</p>
  <table><caption hidden>PPE checklist</caption><tbody>{r.ppe.map(p => <tr key={p.item}><td>{p.item}</td><td>{p.detected ? "Detected" : "Missing"}</td></tr>)}</tbody></table>
  <table><thead><tr><th>Hazard</th><th>Severity</th><th>Corrective action</th></tr></thead><tbody>
    {r.hazards.map((h, i) => <tr key={i}><td>{h.hazard}</td><td><span className={`pill ${h.severity}`}>{h.severity}</span></td><td>{h.remedy}</td></tr>)}</tbody></table>
  <a download="safety-report.json" href={"data:application/json," + encodeURIComponent(JSON.stringify(r, null, 2))}>Download JSON report</a></>} />;

const Crack = () => <ImageTool endpoint="/api/crack" render={r => <>
  <div className="grid"><Stat v={r.defect_type} l="Defect type" /><Stat v={`${r.width_mm} mm`} l="Estimated width" /><div className="stat"><span className={`pill ${r.severity}`}>{r.severity}</span></div></div>
  <p><b>Urgency:</b> {r.urgency}</p><h3>Probable causes</h3><ul>{r.causes.map(c => <li key={c}>{c}</li>)}</ul>
  <h3>Recommended repairs</h3><ul>{r.repairs.map(c => <li key={c}>{c}</li>)}</ul></>} />;

function Planning() {
  const [f, setF] = useState({ structure: "Residential", sqft: 2000, tier: 2, completion: 40 }), [r, setR] = useState(null), [err, setErr] = useState("");
  const set = (k, v) => setF({ ...f, [k]: v });
  const run = async () => { setErr(""); try { setR(await api("/api/valuation", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...f, sqft: +f.sqft, tier: +f.tier, completion: +f.completion }) })); } catch (e) { setErr(e.message); } };
  return <div>
    <label>Structure type</label><select value={f.structure} onChange={e => set("structure", e.target.value)}><option>Residential</option><option>Commercial</option><option>Industrial</option></select>
    <label>Built-up area (sq ft)</label><input type="number" min="1" value={f.sqft} onChange={e => set("sqft", e.target.value)} />
    <label>City tier</label><select value={f.tier} onChange={e => set("tier", e.target.value)}><option value="1">Tier 1</option><option value="2">Tier 2</option><option value="3">Tier 3</option></select>
    <label>Completion: {f.completion}%</label><input type="range" min="0" max="100" value={f.completion} onChange={e => set("completion", e.target.value)} />
    <p><button className="go" onClick={run}>Calculate</button></p>{err && <p className="err" role="alert">{err}</p>}
    {r && <><div className="grid"><Stat v={inr(r.budget_inr)} l="Total budget" /><Stat v={inr(r.spent_inr)} l="Spent so far" /><Stat v={inr(r.market_value_inr)} l="Market valuation" /><Stat v={`${r.steel_kg.toLocaleString()} kg`} l="Steel needed" /><Stat v={r.cement_bags.toLocaleString()} l="Cement bags" /></div>
      <div className="bar"><i style={{ width: f.completion + "%" }} /></div>
      <table><thead><tr><th>Phase</th><th>Share</th><th>Status</th></tr></thead><tbody>{r.schedule.map(s => <tr key={s.phase}><td>{s.phase}</td><td>{s.weight_pct}%</td><td><span className={`pill ${s.status}`}>{s.status}</span></td></tr>)}</tbody></table></>}
  </div>;
}

function Assistant() {
  const [w, setW] = useState("Normal"), [al, setAl] = useState([]), [msgs, setMsgs] = useState([]), [q, setQ] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { api("/api/advisory/" + encodeURIComponent(w)).then(d => setAl(d.alerts)).catch(() => setAl(["Could not load advisory."])); }, [w]);
  const send = async () => {
    if (!q.trim()) return; const m = q; setQ(""); setBusy(true); setMsgs(x => [...x, { me: 1, t: m }]);
    try { const d = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: m }) }); setMsgs(x => [...x, { t: d.reply }]); }
    catch (e) { setMsgs(x => [...x, { t: "Error: " + e.message }]); } finally { setBusy(false); }
  };
  return <div>
    <label>Today's weather</label><select value={w} onChange={e => setW(e.target.value)}>{["Normal", "High Wind", "Heavy Rain", "Extreme Heat"].map(x => <option key={x}>{x}</option>)}</select>
    <div className="note"><b>Site protocol</b><ul>{al.map(a => <li key={a}>{a}</li>)}</ul></div>
    <h3>Ask the site assistant</h3>
    <div className="chat" aria-live="polite">{msgs.length ? msgs.map((m, i) => <p key={i} className={m.me ? "me" : ""}>{m.t}</p>) : <p>Ask about curing time, rebar spacing, scaffolding rules…</p>}</div>
    <input style={{ maxWidth: "none", width: "calc(100% - 100px)" }} aria-label="Your question" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} />
    <button className="go" disabled={busy} onClick={send}>Send</button>
  </div>;
}

const TABS = [["Site safety", Safety], ["Crack analysis", Crack], ["Planning & valuation", Planning], ["Daily assistant", Assistant]];
export default function App() {
  const [i, setI] = useState(0), [mode, setMode] = useState(""); const Tab = TABS[i][1];
  useEffect(() => { api("/api/health").then(d => setMode(d.mode)).catch(() => {}); }, []);
  return <>
    <header><h1>Construction Intelligence Platform</h1><p>Safety, structural and cost insight from site photos{mode && ` · ${mode} mode`}</p></header>
    <nav role="tablist">{TABS.map(([n], k) => <button key={n} role="tab" aria-selected={i === k} className={i === k ? "on" : ""} onClick={() => setI(k)}>{n}</button>)}</nav>
    <main><Tab /></main>
  </>;
}
