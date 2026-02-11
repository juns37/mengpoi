import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  image: string; // pakai image, bukan Svg
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Membaca',
    image: require('@site/static/img/home0.png').default,
    description: (
      <>
        Mengumpulkan informasi dasar: dokumentasi, tutorial, referensi, atau pengalaman orang lain.
      </>
    ),
  },
  {
    title: 'Memahami',
    image: require('@site/static/img/home1.png').default,
    description: (
      <>
        Mencerna apa yang dibaca: mengerti konsep, alur kerja, sebab–akibat, dan risikonya. Bukan sekadar hafal.
      </>
    ),
  },
  {
    title: 'Melakukan (Praktik)',
    image: require('@site/static/img/home2.png').default,
    description: (
      <>
        Menerapkan langsung: mencoba, gagal, memperbaiki, dan mengulang sampai benar-benar bisa.
      </>
    ),
  },
];

function Feature({title, image, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <img
          src={image}
          className={styles.featureSvg}
          alt={title}
        />
      </div>

      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}