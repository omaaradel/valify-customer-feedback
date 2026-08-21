import jwt from 'jsonwebtoken';

const VISITS_TAB_NAME = 'Dashboard Visits';
const TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token';
const SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets';

function loadServiceAccount() {
  const raw = process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
  if (!raw) return null;
  return JSON.parse(Buffer.from(raw, 'base64').toString('utf-8'));
}

// Self-signed JWT service-account grant, exchanged for a Sheets API access
// token. Avoids pulling in googleapis/google-auth-library for a single
// "append a row" call — jsonwebtoken is already a dependency for sessions.
async function getAccessToken(serviceAccount) {
  const now = Math.floor(Date.now() / 1000);
  const assertion = jwt.sign(
    {
      iss: serviceAccount.client_email,
      scope: SHEETS_SCOPE,
      aud: TOKEN_ENDPOINT,
      iat: now,
      exp: now + 3600,
    },
    serviceAccount.private_key,
    { algorithm: 'RS256' }
  );

  const response = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });

  if (!response.ok) {
    throw new Error(`token exchange failed (${response.status})`);
  }

  const data = await response.json();
  return data.access_token;
}

export async function logDashboardVisit(email, userAgent) {
  const serviceAccount = loadServiceAccount();
  const sheetId = process.env.GOOGLE_SHEET_ID;
  if (!serviceAccount || !sheetId) {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SHEET_ID not configured');
  }

  const accessToken = await getAccessToken(serviceAccount);
  const range = encodeURIComponent(`${VISITS_TAB_NAME}!A:C`);
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${range}:append?valueInputOption=USER_ENTERED`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      values: [[email, new Date().toISOString(), userAgent || '']],
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Sheets append failed (${response.status}): ${body}`);
  }

  console.log(`[dashboard-visits] ${email} opened the dashboard`);
}
