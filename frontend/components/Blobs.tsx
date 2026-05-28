export function Blobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0" aria-hidden>
      {/* Top-left — primary indigo ambient */}
      <div
        style={{
          position: 'absolute', top: '-8%', left: '-8%',
          width: 560, height: 560, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(129,140,248,0.09) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      {/* Bottom-right — secondary violet ambient */}
      <div
        style={{
          position: 'absolute', bottom: '5%', right: '-5%',
          width: 420, height: 420, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />
    </div>
  )
}
