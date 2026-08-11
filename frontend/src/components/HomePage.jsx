import Image from "next/image";
import Link from "next/link";
import melbourneHero from "../../public/images/melbourne-cbd-hero.png";
import AppIcon from "./app/AppIcon.jsx";

const FEATURES = [
  {
    title: "Plan calmer routes",
    description: "Compare sensory-aware routes and travel with confidence.",
    icon: "route",
    tone: "green",
    href: "/plan",
  },
  {
    title: "Find refuges",
    description: "Discover quiet, welcoming spaces when you need a break.",
    icon: "leaf",
    tone: "purple",
    href: "/refuges",
  },
  {
    title: "Get real-time alerts",
    description: "Stay informed about disruptions and sensory changes.",
    icon: "bell",
    tone: "amber",
  },
  {
    title: "Personalise your experience",
    description: "Adjust preferences to suit your sensory needs.",
    icon: "sliders",
    tone: "blue",
    href: "/settings",
  },
];

function FeatureCard({ feature }) {
  const content = (
    <>
      <span className="feature-card__icon"><AppIcon name={feature.icon} size={29} /></span>
      <div>
        <h2>{feature.title}</h2>
        <p>{feature.description}</p>
      </div>
      <AppIcon className="feature-card__watermark" name={feature.icon} size={108} />
    </>
  );

  if (feature.href) {
    return (
      <Link
        className={`feature-card feature-card--${feature.tone} feature-card--link`}
        href={feature.href}
        aria-label={feature.title}
      >
        {content}
      </Link>
    );
  }

  return (
    <article className={`feature-card feature-card--${feature.tone}`}>
      {content}
    </article>
  );
}

export default function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero" aria-labelledby="home-hero-heading">
        <div className="home-hero__copy">
          <h1 id="home-hero-heading">You deserve a <span>calmer journey.</span></h1>
          <p>eScape helps you find sensory-aware routes, refuges, and real-time alerts in Melbourne CBD.</p>
        </div>
        <div className="home-hero__visual">
          <Image
            src={melbourneHero}
            alt="Melbourne CBD skyline and Princes Bridge beside the Yarra River"
            fill
            priority
            sizes="(max-width: 767px) 100vw, 66vw"
          />
        </div>
      </section>

      <section className="feature-grid" aria-label="What eScape can help with">
        {FEATURES.map((feature) => <FeatureCard key={feature.title} feature={feature} />)}
      </section>
    </div>
  );
}
