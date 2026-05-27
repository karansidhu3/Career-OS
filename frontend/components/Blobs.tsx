export function Blobs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0" aria-hidden>
      <div
        style={{
          position: 'absolute', top: '-10%', left: '-5%',
          width: 600, height: 600, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(165,180,252,0.25) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      <div
        style={{
          position: 'absolute', top: '20%', right: '-10%',
          width: 500, height: 500, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(167,243,208,0.2) 0%, transparent 70%)',
          filter: 'blur(50px)',
        }}
      />
      <div
        style={{
          position: 'absolute', bottom: '10%', left: '30%',
          width: 450, height: 450, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(253,186,116,0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      <div
        style={{
          position: 'absolute', top: '50%', left: '20%',
          width: 300, height: 300, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(165,243,252,0.2) 0%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
    </div>
  )
}
