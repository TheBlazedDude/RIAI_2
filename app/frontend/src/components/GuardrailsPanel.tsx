import React, { useEffect, useState } from 'react'

export type Guardrails = {
  max_tokens: number
  pii_regex?: string[]
  blocked_categories?: string[]
  allowed_file_types?: string[]
}

export default function GuardrailsPanel({ initial, onChange }: { initial?: Guardrails, onChange?: (g: Guardrails)=>void }){
  const [policy, setPolicy] = useState<Guardrails>({
    max_tokens: initial?.max_tokens ?? 256,
    pii_regex: initial?.pii_regex ?? [],
    blocked_categories: initial?.blocked_categories ?? [],
    allowed_file_types: initial?.allowed_file_types ?? ['.json']
  })

  useEffect(()=>{ if(initial){ setPolicy({
    max_tokens: initial.max_tokens,
    pii_regex: initial.pii_regex || [],
    blocked_categories: initial.blocked_categories || [],
    allowed_file_types: initial.allowed_file_types || ['.json']
  }) } }, [initial])

  function update(next: Guardrails){
    setPolicy(next)
    onChange && onChange(next)
  }

  return (
    <div style={{display:'grid', gap:12}}>
      <div>
        <label>Max tokens</label>
        <input type="number" value={policy.max_tokens} min={1}
               onChange={e=> update({ ...policy, max_tokens: Math.max(1, Number(e.target.value)||1) })}
               style={{marginLeft:8, width:120}}/>
      </div>
      <div>
        <label>PII regex (comma-separated)</label>
        <input type="text" value={(policy.pii_regex||[]).join(',')}
               onChange={e=> update({ ...policy, pii_regex: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) })}
               style={{marginLeft:8, width:'100%'}}/>
      </div>
      <div>
        <label>Blocked categories (comma-separated)</label>
        <input type="text" value={(policy.blocked_categories||[]).join(',')}
               onChange={e=> update({ ...policy, blocked_categories: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) })}
               style={{marginLeft:8, width:'100%'}}/>
      </div>
      <div>
        <label>Allowed file types (comma-separated)</label>
        <input type="text" value={(policy.allowed_file_types||[]).join(',')}
               onChange={e=> update({ ...policy, allowed_file_types: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) })}
               style={{marginLeft:8, width:'100%'}}/>
      </div>
      <div style={{fontSize:12, color:'#374151'}}>Guardrails apply immediately to all outputs. Blocks are logged under artifacts\\traces.</div>
    </div>
  )
}
