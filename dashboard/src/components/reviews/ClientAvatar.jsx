const LOGOS = {
  Amazon: '/logos/amazon.png',
  Thndr: '/logos/thndr.png',
  Klivvr: '/logos/klivvr.png',
  Rabbit: '/logos/rabbit.png',
  ADIB: '/logos/adib.png',
  Midbank: '/logos/midbank.png',
  Raya: '/logos/raya.png',
  Khazna: '/logos/khazna.png',
};

// 40px circle avatar: the client's real logo on a white chip, contained (not
// cropped) so logos of any aspect ratio or background color read cleanly.
// Falls back to a navy initial-letter circle for any client without a logo.
function ClientAvatar({ client }) {
  const logoSrc = LOGOS[client];

  if (logoSrc) {
    return (
      <div
        className="flex flex-shrink-0 items-center justify-center overflow-hidden"
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          background: '#FFFFFF',
          border: '1px solid var(--color-border)',
        }}
      >
        <img
          src={logoSrc}
          alt={`${client} logo`}
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: '4px' }}
        />
      </div>
    );
  }

  const initial = (client || '?').trim().charAt(0).toUpperCase();
  return (
    <div
      aria-hidden="true"
      className="flex flex-shrink-0 items-center justify-center"
      style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        background: 'var(--color-navy)',
        color: '#FFFFFF',
        fontWeight: 'var(--font-weight-heading)',
        fontSize: 'var(--font-size-card-text)',
      }}
    >
      {initial}
    </div>
  );
}

export default ClientAvatar;
