import jwt from 'jsonwebtoken';

const SESSION_COOKIE_NAME = 'session_token';
const SESSION_MAX_AGE_SECONDS = 86400;

// Verifies the Google ID token against Google's own tokeninfo endpoint rather
// than a JWKS library, since this is the one call this route needs and it
// keeps the dependency list to just jsonwebtoken for our own session token.
async function verifyGoogleToken(credential) {
  const response = await fetch(
    `https://oauth2.googleapis.com/tokeninfo?id_token=${encodeURIComponent(credential)}`
  );
  if (!response.ok) return null;
  return response.json();
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method_not_allowed' });
    return;
  }

  const credential = req.body && req.body.credential;
  if (!credential) {
    res.status(400).json({ error: 'missing_credential' });
    return;
  }

  let payload;
  try {
    payload = await verifyGoogleToken(credential);
  } catch {
    payload = null;
  }

  if (!payload || payload.aud !== process.env.VITE_GOOGLE_CLIENT_ID) {
    res.status(401).json({ error: 'invalid_token' });
    return;
  }

  const email = String(payload.email || '').toLowerCase();
  const allowedEmails = String(process.env.ALLOWED_EMAILS || '')
    .split(',')
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);

  if (!email || !allowedEmails.includes(email)) {
    res.status(403).json({ error: 'not_authorized' });
    return;
  }

  const token = jwt.sign({ email }, process.env.SESSION_SECRET, {
    expiresIn: SESSION_MAX_AGE_SECONDS,
  });

  res.setHeader(
    'Set-Cookie',
    `${SESSION_COOKIE_NAME}=${token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${SESSION_MAX_AGE_SECONDS}`
  );
  res.status(200).json({ authenticated: true, email });
}
