import React from 'react'

export function StatusChip({ status }: { status: 'Not started'|'In progress'|'Ready'|'Draft'|'Training'|'Evaluating'|'Promoted'|string }){
  const color = status === 'Ready' ? '#065f46' : status === 'In progress' ? '#92400e' : '#374151'
  const bg = status === 'Ready' ? '#ecfdf5' : status === 'In progress' ? '#fff7ed' : '#f3f4f6'
  return (
    <span style={{fontSize:12, padding:'2px 8px', borderRadius:999, background:bg, color}}>{status}</span>
  )
}
