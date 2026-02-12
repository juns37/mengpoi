import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Perkenalan - 5min ⏱️
          </Link>
        </div>
      </div>
    </header>
  );
}

// Komponen Support (Tutorial Cards)
function SupportSection() {
const cards = [
  {
    title: 'Marble',
    description: 'RN12 Turbo / Poco F5.',
    linkText: 'Dokumentasi',
    link: '/marble/intro',
    // Ganti ikon dengan tag img
    icon: <img src="img/marble.png" alt="Marble Icon" className={styles.cardImageIcon} />,
  },
];


  return (
    <section className={styles.supportSection}>
      <div className="container">
        <div className="row">

          {cards.map((card, idx) => (

            <div
              key={idx}
              className={clsx('col col--6', styles.cardCol)}
            >

              {/* LINK MEMBUNGKUS SELURUH CARD */}
              <Link
                to={card.link}
                className={styles.cardLink}
              >

<div className={clsx('card', styles.customCard)}>
  <div className="card__body">
    {/* Bungkus Icon dan Title di sini */}
    <div className={styles.headerWrapper}>
      <div className={styles.iconWrapper}>
        {card.icon}
      </div>
      <Heading as="h3" className={styles.cardTitle}>
        {card.title}
      </Heading>
    </div>

    <p>{card.description}</p>
  </div>

  <div className="card__footer">
    <span className={styles.view}>
      {card.linkText} →
    </span>
  </div>
</div>


              </Link>

            </div>

          ))}

        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`Hello from ${siteConfig.title}`}
      description="Description will go into a meta tag in <head />">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <SupportSection />
      </main>
    </Layout>
  );
}
