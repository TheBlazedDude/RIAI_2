import React from 'react'

type Step = { title: string, content: React.ReactNode }

export default function Wizard({ steps, current }: { steps: Step[], current: number }){
  return (
    <div>
      <div style={{display:'flex', gap:8, marginBottom:12}}>
        {steps.map((s, i)=> (
          <div key={i} style={{padding:'6px 10px', borderRadius:999, border:'1px solid #e5e7eb', background: i===current? '#eef2ff':'#fff'}}>
            {i+1}. {s.title}
          </div>
        ))}
      </div>
      <div>
        {steps[current]?.content}
      </div>
    </div>
  )
}
