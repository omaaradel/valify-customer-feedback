// 40px circle avatar: first letter of the client name, navy background, white text.
function ClientAvatar({ client }) {
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
