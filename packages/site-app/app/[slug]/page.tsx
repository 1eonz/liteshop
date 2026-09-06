import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { SiteRenderer } from '../../src/components/SiteRenderer';
import { getSitePage, sitePages } from '../../src/site-data';

interface SitePageProps {
  params: { slug: string };
}

export function generateStaticParams(): Array<{ slug: string }> {
  return Object.keys(sitePages)
    .filter((slug) => slug !== 'home')
    .map((slug) => ({ slug }));
}

export function generateMetadata({ params }: SitePageProps): Metadata {
  const page = getSitePage(params.slug);
  if (!page) return { title: '页面不存在 | LiteShop' };
  return {
    title: page.seo.title,
    description: page.seo.description,
    keywords: page.seo.keywords,
    robots: page.seo.noIndex ? { index: false, follow: false } : undefined,
  };
}

export default function SitePage({ params }: SitePageProps): JSX.Element {
  const page = getSitePage(params.slug);
  if (!page) notFound();
  return <SiteRenderer page={page} />;
}
