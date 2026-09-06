import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { SiteRenderer } from '../../src/components/SiteRenderer';
import { sitePages } from '../../src/site-data';
import { loadSitePage } from '../../src/site-data.server';

interface SitePageProps {
  params: { slug: string };
}

export function generateStaticParams(): Array<{ slug: string }> {
  return Object.keys(sitePages)
    .filter((slug) => slug !== 'home')
    .map((slug) => ({ slug }));
}

export const revalidate = 60;

export async function generateMetadata({ params }: SitePageProps): Promise<Metadata> {
  const page = await loadSitePage(params.slug);
  if (!page) return { title: '页面不存在 | LiteShop' };
  return {
    title: page.seo.title,
    description: page.seo.description,
    keywords: page.seo.keywords,
    robots: page.seo.noIndex ? { index: false, follow: false } : undefined,
  };
}

export default async function SitePage({ params }: SitePageProps): Promise<JSX.Element> {
  const page = await loadSitePage(params.slug);
  if (!page) notFound();
  return <SiteRenderer page={page} />;
}
