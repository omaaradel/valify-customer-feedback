import jwt from 'jsonwebtoken';

const SESSION_COOKIE_NAME = 'session_token';

function parseCookies(header) {
  const cookies = {};
  if (!header) return cookies;
  header.split('; ').forEach((pair) => {
    const separatorIndex = pair.indexOf('=');
    if (separatorIndex === -1) return;
    const key = pair.slice(0, separatorIndex).trim();
    const value = pair.slice(separatorIndex + 1).trim();
    cookies[key] = value;
  });
  return cookies;
}

export default function handler(req, res) {
  if (req.method !== 'GET') {
    res.status(405).json({ authenticated: false });
    return;
  }

  const cookies = parseCookies(req.headers.cookie);
  const token = cookies[SESSION_COOKIE_NAME];

  if (!token) {
    res.status(401).json({ authenticated: false });
    return;
  }

  try {
    const payload = jwt.verify(token, process.env.SESSION_SECRET);
    res.status(200).json({ authenticated: true, email: payload.email });
  } catch {
    res.status(401).json({ authenticated: false });
  }
}
