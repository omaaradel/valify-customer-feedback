import { useState } from 'react';

// #92400E is used as text (not var(--color-neutral) itself) because the raw
// token fails WCAG AA as text, see the contrast gap already logged in
// HANDOFF.md's open backlog; this darker shade of the same amber passes at
// 7.1:1 against a near-white background.
const BANNER_TEXT_COLOR = '#92400E';

function WarningIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <path
        d="M10 2.5L18 16.5H2L10 2.5Z"
        stroke={BANNER_TEXT_COLOR}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M10 8V12" stroke={BANNER_TEXT_COLOR} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="10" cy="14.5" r="0.9" fill={BANNER_TEXT_COLOR} />
    </svg>
  );
}

function DismissIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path
        d="M1 1L13 13M13 1L1 13"
        stroke={BANNER_TEXT_COLOR}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ConfidenceBanner() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div
      className="flex items-center"
      style={{
        gap: 'var(--space-2)',
        borderRadius: 'var(--radius-card)',
        border: '1px solid color-mix(in srgb, var(--color-neutral) 30%, transparent)',
        background: 'color-mix(in srgb, var(--color-neutral) 12%, transparent)',
        padding: 'var(--space-2)',
        color: BANNER_TEXT_COLOR,
      }}
    >
      <WarningIcon />
      <p
        className="flex-1 whitespace-nowrap overflow-hidden text-ellipsis"
        style={{
          margin: 0,
          fontSize: 'var(--font-size-body)',
          fontWeight: 'var(--font-weight-body)',
          lineHeight: 'var(--line-height-body)',
          color: BANNER_TEXT_COLOR,
        }}
      >
        Scope classifications are AI-inferred and may not precisely distinguish Valify-specific
        friction from broader client app issues. Interpret with appropriate caution.
      </p>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        style={{
          flexShrink: 0,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 'var(--space-1)',
          display: 'flex',
        }}
      >
        <DismissIcon />
      </button>
    </div>
  );
}

export default ConfidenceBanner;
