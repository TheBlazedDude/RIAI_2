import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getModules, saveWorkspace, getWorkspace } from '../lib/api'

export default function ModuleSelection(){
  const navigate = useNavigate()
  const [modules, setModules] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function load(){
    setLoading(true)
    setError(null)
    try{
      const [mods, ws] = await Promise.all([getModules(), getWorkspace()])
      // Hide lexicon-wordnet3 from selection (data dependency)
      const arr = (mods.modules || []).filter((m:any)=> m.id !== 'lexicon-wordnet3')
      setModules(arr)
      const sel = (ws?.selected_modules || []) as string[]
      if(Array.isArray(sel)){
        const map: Record<string, boolean> = {}
        sel.forEach(id => { map[id] = true })
        setSelected(map)
      }
    }catch(e:any){
      setError(String(e))
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ load() },[])

  function toggle(id: string){
    setSelected(prev=>({ ...prev, [id]: !prev[id] }))
  }

  async function onContinue(){
    setMessage(null)
    const chosen = Object.entries(selected).filter(([,v])=>v).map(([k])=>k)
    if(chosen.length === 0){
      setMessage('Select at least one module to continue.')
      return
    }
    try{
      setSaving(true)
      await saveWorkspace(chosen)
      setMessage('Selection saved to pending workspace.')
    }catch(e:any){
      setMessage('Failed to save selection: '+ String(e))
    }finally{
      setSaving(false)
    }
  }

  if(loading) return <div>Loading modules…</div>
  if(error) return (
    <div style={{color:'red'}}>
      <div>Error: {error}</div>
      <div style={{marginTop:8}}>
        <button onClick={load}>Retry</button>
      </div>
    </div>
  )

  const selectedCount = Object.values(selected).filter(Boolean).length

  return (
    <div>
      <h2>Choose your modules</h2>
      <p>Modules run fully offline and can be added or removed at any time.</p>
      <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(260px,1fr))', gap:16}}>
        {modules.map(m => (
          <div key={m.id} style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <strong>{m.name || m.id}</strong>
              <input type="checkbox" checked={!!selected[m.id]} onChange={()=>toggle(m.id)} />
            </div>
            <div style={{fontSize:12, color:'#374151', marginTop:8}}>{m.description || ''}</div>
            {m.error && <div style={{color:'red', marginTop:8}}>Manifest error: {m.error}</div>}
          </div>
        ))}
      </div>
      <div style={{display:'flex', justifyContent:'flex-end', gap:12, marginTop:16}}>
        <button disabled={saving || selectedCount===0} onClick={async()=>{ await onContinue(); }}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button disabled={saving || selectedCount===0} onClick={async()=>{ await onContinue(); navigate('/nns') }}>
          {saving ? 'Saving…' : 'Save & Continue → Neural Nets'}
        </button>
      </div>
      {message && <div style={{marginTop:8, fontSize:12, color: message.startsWith('Failed')? 'red':'#065f46'}}>{message}</div>}
    </div>
  )
}
