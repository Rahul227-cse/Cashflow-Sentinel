import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const api = (path, options) => fetch(`http://localhost:5000/api${path}`, options).then(async r => {
  if (r.ok) return r.json();
  const data = await r.json().catch(() => null);
  throw new Error((data && (data.error || data.message)) || `Request failed (${r.status})`);
});
const rupees = n => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n || 0);
const Badge = ({value}) => <span className={`badge ${value}`}>{value}</span>;

function App() {
  const [dashboard,setDashboard]=useState(), [invoices,setInvoices]=useState([]), [alerts,setAlerts]=useState([]), [collections,setCollections]=useState([]), [tab,setTab]=useState('Overview'), [query,setQuery]=useState(''), [error,setError]=useState(''), [reconStatus,setReconStatus]=useState(null), [running,setRunning]=useState(false);
  const load=async()=>{try { const [d,i,a,c]=await Promise.all([api('/dashboard'),api('/invoices'),api('/alerts'),api('/collections')]); setDashboard(d);setInvoices(i.items);setAlerts(a);setCollections(c); }catch(e){setError('The API is unavailable. Start the Flask server and reload.')}};
  useEffect(()=>{load()},[]);
  const run=async()=>{
    if(running) return;
    setRunning(true);
    setReconStatus(null);
    try {
      const res = await api('/reconciliation/run',{method:'POST'});
      setReconStatus({message:`${res.message} (${res.alerts_found} discrepancies detected)`, tone:'low'});
      await load();
    } catch(e) {
      setReconStatus({message:e.message || 'Reconciliation failed', tone:'high'});
    } finally {
      setRunning(false);
    }
  };
  if(error) return <main className="state"><h1>CashFlow Sentinel</h1><p>{error}</p></main>;
  if(!dashboard) return <main className="state">Loading financial intelligence…</main>;
  const metrics=[['Outstanding',dashboard.metrics.outstanding,'blue'],['Overdue',dashboard.metrics.overdue,'amber'],['High-risk invoices',dashboard.metrics.high_risk_count,'rose'],['Potential discrepancies',dashboard.metrics.discrepancy_count,'violet']];
  const filtered=invoices.filter(i => `${i.invoice_number} ${i.customer_name}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="shell"><aside><div className="brand"><span>◈</span> CashFlow<br/><b>Sentinel</b></div><small>EARLY-WARNING PROTOTYPE</small>{['Overview','Invoice registry','Discrepancies','Collections'].map(x=><button className={tab===x?'nav active':'nav'} onClick={()=>setTab(x)} key={x}>{x}</button>)}<div className="prototype">Synthetic demonstration data<br/>Human review required</div></aside><main><header><div><p className="eyebrow">FINANCIAL INTELLIGENCE</p><h1>{tab}</h1><p className="muted">Reporting date: {dashboard.reporting_date}{reconStatus && <span style={{marginLeft:'12px'}} className={`badge ${reconStatus.tone}`}>{reconStatus.message}</span>}</p></div><button className="primary" onClick={run} disabled={running}>{running ? 'Running reconciliation…' : 'Run reconciliation'}</button></header>
  {tab==='Overview' && <><section className="metrics">{metrics.map(([label,value,tone])=><article className={`metric ${tone}`} key={label}><p>{label}</p><strong>{typeof value==='number' && label.includes('invoices') || label.includes('discrepancies') ? value : rupees(value)}</strong></article>)}</section><section className="grid"><Panel title="Expected collections"><div className="bars">{dashboard.expected_collections.map(x=><div key={x.bucket}><span>{x.bucket}</span><b style={{width:`${Math.max(8,x.amount/4500)}%`}}></b><em>{rupees(x.amount)}</em></div>)}</div></Panel><Panel title="Priority collection actions">{dashboard.top_collections.map(x=><div className="action" key={x.invoice_id}><div><b>{x.customer_name}</b><p>{x.reason}</p></div><strong>{x.priority_score}</strong></div>)}</Panel></section><Panel title="Recent alerts">{dashboard.recent_alerts.map(a=><Alert data={a} key={a.id}/>)}</Panel></>}
  {tab==='Invoice registry' && <><input className="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search invoice or customer"/><Panel title={`${filtered.length} invoices`}><table><thead><tr><th>Invoice</th><th>Customer</th><th>Due date</th><th>Open balance</th><th>Risk</th></tr></thead><tbody>{filtered.map(i=><tr key={i.id}><td><b>{i.invoice_number}</b><br/><small>{i.id}</small></td><td>{i.customer_name}</td><td>{i.due_date}</td><td>{rupees(i.outstanding)}</td><td><Badge value={i.risk.level}/></td></tr>)}</tbody></table></Panel></>}
  {tab==='Discrepancies' && <Panel title="Suspected discrepancies">{alerts.map(a=><Alert data={a} key={a.id}/>)}</Panel>}
  {tab==='Collections' && <Panel title="Ranked collection queue">{collections.map(x=><div className="action" key={x.invoice_id}><div><Badge value={x.priority_score>=70?'high':'medium'}/> <b>{x.invoice_number} · {x.customer_name}</b><p>{x.suggested_action}</p></div><div><strong>{rupees(x.outstanding)}</strong><p>Priority {x.priority_score}/100</p></div></div>)}</Panel>}
  </main></div>
}
function Panel({title,children}){return <section className="panel"><h2>{title}</h2>{children}</section>}
function Alert({data:a}){return <div className="alert"><Badge value={a.severity}/><div><b>{a.type}</b><p>{a.reason} <span>• {a.suggested_step}</span></p></div><strong>{a.discrepancy_amount ? rupees(a.discrepancy_amount):''}</strong></div>}
createRoot(document.getElementById('root')).render(<App/>);
