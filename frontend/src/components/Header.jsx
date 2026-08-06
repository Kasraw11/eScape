export default function Header() {
  return (
    <header className="site-header">
      <a className="brand" href="#main-content" aria-label="eScape home">
        <span className="brand__mark" aria-hidden="true">e</span>
        <span className="brand__copy">
          <strong>eScape</strong>
          <small>Calmer journeys through Melbourne CBD</small>
        </span>
      </a>

      <nav className="desktop-nav" aria-label="Primary navigation">
        <a className="desktop-nav__active" href="#journey-form" aria-current="page">Plan journey</a>
        <a href="#about">About</a>
        <a href="#travel-mode">Settings</a>
      </nav>

      <details className="mobile-nav">
        <summary aria-label="Open navigation menu">
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </summary>
        <nav aria-label="Mobile navigation">
          <a href="#journey-form">Plan journey</a>
          <a href="#about">About</a>
          <a href="#travel-mode">Settings</a>
        </nav>
      </details>
    </header>
  );
}
