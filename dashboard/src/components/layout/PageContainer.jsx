// Centers page content, caps its width, and spaces sections vertically on
// the design system's 8pt grid. Horizontal padding narrows on mobile.
function PageContainer({ children }) {
  return (
    <div
      className="mx-auto flex flex-col px-4 md:px-8"
      style={{
        maxWidth: '1280px',
        gap: 'var(--section-gap)',
        paddingTop: 'var(--section-gap)',
        paddingBottom: 'var(--section-gap)',
      }}
    >
      {children}
    </div>
  );
}

export default PageContainer;
