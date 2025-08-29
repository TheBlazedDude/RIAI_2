import React, { useEffect, useState } from 'react'
import { getReadiness, getModules, runtimePost, ingestDataset, trainJob, evaluateJob, latestMetrics } from '../lib/api'
import ModulePanelHost from '../components/ModulePanelHost'

export default function AIWorkspace(){
  const [readiness, setReadiness] = useState<any>(null)
  const [modules, setModules] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [chat, setChat] = useState('')
  const [chatOut, setChatOut] = useState<any>(null)
  // Local state used by utility actions (dataset ingest, train/eval, metrics)
  const [busyUpload, setBusyUpload] = useState(false)
  const [dsFormat, setDsFormat] = useState<'jsonl'|'text'|'csv'>('jsonl')
  const [dsContent, setDsContent] = useState('')
  const [busyTrain, setBusyTrain] = useState(false)
  const [busyEval, setBusyEval] = useState(false)
  const [seed, setSeed] = useState<number>(1337)
  const [chatMetrics, setChatMetrics] = useState<any>(null)

  useEffect(()=>{
    Promise.all([getReadiness(), getModules()])
      .then(([r, m])=>{ setReadiness(r); setModules(m.modules||[]) })
      .catch(e=> setError(String(e)))
      .finally(()=> setLoading(false))
  },[])

  async function retryReadiness(){
    try{
      setRetrying(true)
      const r = await getReadiness()
      setReadiness(r)
    }catch(e){
    }finally{
      setRetrying(false)
    }
  }

  async function sendChat(){
    try{
      const res = await runtimePost({ text: chat })
      // Prefer the model's guarded answer; fall back to raw answer; as last resort, show processed
      const ans = (res && res.answer) ? (res.answer.guarded || { result: res.answer.raw, actions: [] }) : null
      setChatOut(ans || res?.processed || res)
    }catch(e){
      setChatOut({ error: String(e) })
    }
  }


  async function uploadDataset(){
    try{
      setBusyUpload(true)
      const res = await ingestDataset({ format: dsFormat, content: dsContent, capability: 'chat' })
      // optional: clear content after upload
      setDsContent('')
    }catch(e){
      // swallow for now
    }finally{
      setBusyUpload(false)
    }
  }

  async function runTrain(){
    try{
      setBusyTrain(true)
      await trainJob('chat-core', seed)
    }catch(e){
    }finally{
      setBusyTrain(false)
    }
  }

  async function runEvaluate(){
    try{
      setBusyEval(true)
      const modelId = `chat_retrieval_${seed}`
      await evaluateJob('chat-core', seed, modelId)
      await loadChatMetrics()
    }catch(e){
    }finally{
      setBusyEval(false)
    }
  }

  async function loadChatMetrics(){
    try{
      const res = await latestMetrics('chat')
      setChatMetrics(res?.metrics || null)
    }catch(e){
      setChatMetrics(null)
    }
  }

  if(loading) return <div>Loading workspace…</div>
  if(error) return <div style={{color:'red'}}>Error: {error}</div>

  const blocked = readiness?.status !== 'ready'

  return (
    <div>
      <h2>AI Workspace (Offline)</h2>
      <div style={{marginBottom:12}}>
        Readiness: <strong style={{color: !blocked ? 'green' : 'orange'}}>{readiness?.status}</strong>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 360px', gap:12, filter: blocked ? 'blur(1px)' : 'none'}}>
        <div style={{display:'grid', gap:12}}>
          <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
            <strong>Chat Panel</strong>
            <div style={{fontSize:12, color:'#374151', marginTop:4}}>Offline chat with guardrails applied.</div>
            <div style={{marginTop:8, display:'flex', gap:8}}>
              <input value={chat} onChange={e=> setChat(e.target.value)} placeholder="Type your prompt…" style={{flex:1, padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
              <button onClick={sendChat}>Send</button>
            </div>
            {chatOut && (
              <div style={{marginTop:8, fontSize:12}}>
                <div><strong>Result:</strong> {chatOut?.result || JSON.stringify(chatOut)}</div>
                {Array.isArray(chatOut?.actions) && chatOut.actions.length>0 && (
                  <div style={{marginTop:4}}>Actions: {chatOut.actions.map((a:any)=>a.type).join(', ')}</div>
                )}
              </div>
            )}
          </div>
          <ModulePanelHost modules={modules} />
        </div>
        <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
          <div style={{fontSize:12, color:'#374151'}}>Workspace is for runtime use only. Training, dataset uploads, and guardrails configuration are available in the Lab tab.</div>
        </div>
      </div>

      {blocked && (
        <div style={{position:'fixed', inset:0 as any, background:'rgba(0,0,0,0.4)', display:'flex', alignItems:'center', justifyContent:'center'}}>
          <div style={{background:'#fff', borderRadius:12, padding:16, width:600, boxShadow:'0 10px 30px rgba(0,0,0,0.2)'}}>
            <div style={{fontWeight:600, marginBottom:8}}>Readiness Check Failed</div>
            <div style={{fontSize:13, color:'#374151', marginBottom:8}}>Some assets are missing. Fix items below, then retry.</div>
            <ul style={{maxHeight:240, overflow:'auto', margin:'8px 0', paddingLeft:18}}>
              {(readiness?.errors||[]).map((e:any, idx:number)=> (
                <li key={idx} style={{marginBottom:6}}>
                  <div><strong>{e.error_code}</strong>: {e.human_message}</div>
                  <div style={{fontSize:12, color:'#6b7280'}}>Hint: {e.hint} — Logs: {e.where_to_find_logs}</div>
                </li>
              ))}
            </ul>
            <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginTop:12}}>
              <button onClick={retryReadiness} disabled={retrying}>{retrying? 'Retrying…' : 'Retry Readiness Check'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
