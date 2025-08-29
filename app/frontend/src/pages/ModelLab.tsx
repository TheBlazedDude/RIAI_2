import React, { useEffect, useState } from 'react'
import { latestMetrics, getGuardrails, setGuardrails, ingestDataset, trainJob, evaluateJob, getWorkspace } from '../lib/api'
import MetricsCharts from '../components/MetricsCharts'
import GuardrailsPanel, { Guardrails } from '../components/GuardrailsPanel'

export default function ModelLab(){
  const [chatMetrics, setChatMetrics] = useState<any>(null)
  const [predMetrics, setPredMetrics] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [guard, setGuard] = useState<Guardrails | null>(null)
  const [savingGuard, setSavingGuard] = useState(false)
  const [dsFormat, setDsFormat] = useState<'text'|'jsonl'|'csv'>('text')
  const [dsContent, setDsContent] = useState('')
  const [busyUpload, setBusyUpload] = useState(false)
  const [busyChatTrain, setBusyChatTrain] = useState(false)
  const [busyChatEval, setBusyChatEval] = useState(false)
  const [busyPredEval, setBusyPredEval] = useState(false)
  const [ws, setWs] = useState<any>(null)

  async function load(){
    setLoading(true)
    try{
      const [chat, pred, g, w] = await Promise.all([
        latestMetrics('chat'),
        latestMetrics('predictor'),
        getGuardrails(),
        getWorkspace()
      ])
      setChatMetrics(chat?.metrics || null)
      setPredMetrics(pred?.metrics || null)
      setGuard(g)
      setWs(w)
    }catch(e){
      // ignore for now
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ load() }, [])

  async function saveGuard(){
    if(!guard) return
    try{ setSavingGuard(true); await setGuardrails(guard) } finally { setSavingGuard(false) }
  }

  async function upload(){
    try{ setBusyUpload(true); await ingestDataset({ format: dsFormat, content: dsContent, capability: 'chat' }); setDsContent('') } finally { setBusyUpload(false) }
  }

  async function trainChat(){
    try{ setBusyChatTrain(true); await trainJob('chat-core', ws?.seed ?? 1337) } finally { setBusyChatTrain(false) }
  }

  async function evalChat(){
    try{ setBusyChatEval(true); const mid = `chat_retrieval_${ws?.seed ?? 1337}`; await evaluateJob('chat-core', ws?.seed ?? 1337, mid); await load() } finally { setBusyChatEval(false) }
  }

  async function evalPred(){
    try{ setBusyPredEval(true); const mid = `predictor_ma_${ws?.seed ?? 1337}`; await evaluateJob('predictor-finance', ws?.seed ?? 1337, mid); await load() } finally { setBusyPredEval(false) }
  }

  return (
    <div>
      <h2>Model Lab</h2>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12}}>
        <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
          <strong>Guardrails (Admin)</strong>
          <div style={{marginTop:8}}>{guard && <GuardrailsPanel initial={guard} onChange={setGuard} />}</div>
          <div style={{marginTop:8}}>
            <button onClick={saveGuard} disabled={savingGuard}>{savingGuard? 'Saving…':'Save Guardrails'}</button>
          </div>
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
          <strong>Datasets — Upload (Chat)</strong>
          <div style={{display:'flex', gap:8, alignItems:'center', marginTop:8}}>
            <label>Format</label>
            <select value={dsFormat} onChange={e=> setDsFormat(e.target.value as any)}>
              <option value="text">text</option>
              <option value="jsonl">jsonl</option>
              <option value="csv">csv</option>
            </select>
            <button onClick={upload} disabled={busyUpload}>{busyUpload? 'Uploading…':'Upload'}</button>
          </div>
          <textarea placeholder="Paste data here (text/jsonl/csv)" value={dsContent} onChange={e=> setDsContent(e.target.value)}
                    style={{width:'100%', height:100, marginTop:8, padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
        </div>
      </div>

      <div style={{display:'flex', gap:12, marginBottom:12}}>
        <button onClick={load} disabled={loading}>{loading? 'Refreshing…':'Refresh metrics'}</button>
        <button onClick={trainChat} disabled={busyChatTrain}> {busyChatTrain? 'Training chat…':'Train Chat (seed from workspace)'} </button>
        <button onClick={evalChat} disabled={busyChatEval}> {busyChatEval? 'Evaluating chat…':'Evaluate Chat'} </button>
        <button onClick={evalPred} disabled={busyPredEval}> {busyPredEval? 'Evaluating predictor…':'Evaluate Predictor'} </button>
        <div style={{fontSize:12, color:'#6b7280'}}>Seed: {ws?.seed ?? 1337}</div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
        <div>
          <h3>Chat — Latest</h3>
          {chatMetrics ? (
            <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
              <div style={{fontSize:12, color:'#374151'}}>model: {chatMetrics.model_id || 'n/a'}</div>
              <div style={{marginTop:8}}>Latency p50: {chatMetrics.latency_ms?.p50 ?? '—'} ms; p95: {chatMetrics.latency_ms?.p95 ?? '—'} ms</div>
              <div>Grounding hit rate: {chatMetrics.grounding_hit_rate ?? '—'}</div>
              <div style={{marginTop:8}}>
                <MetricsCharts capability="chat" modelId={chatMetrics.model_id} />
              </div>
            </div>
          ) : <div style={{fontSize:12, color:'#6b7280'}}>No chat metrics yet.</div>}
        </div>
        <div>
          <h3>Predictor — Latest</h3>
          {predMetrics ? (
            <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
              <div style={{fontSize:12, color:'#374151'}}>model: {predMetrics.model_id || 'n/a'}</div>
              <div style={{marginTop:8}}>MAE: {predMetrics.mae ?? '—'} | RMSE: {predMetrics.rmse ?? '—'} | MAPE: {predMetrics.mape ?? '—'}</div>
              <div>n: {predMetrics.n ?? '—'}</div>
              <div style={{marginTop:8}}>
                <MetricsCharts capability="predictor" modelId={predMetrics.model_id} />
              </div>
            </div>
          ) : <div style={{fontSize:12, color:'#6b7280'}}>No predictor metrics yet.</div>}
        </div>
      </div>
    </div>
  )
}
