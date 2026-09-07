import type { Metadata } from 'next';
import { SiteRenderer } from '../src/components/SiteRenderer';
import { loadSitePage } from '../src/site-data.server';

export const revalidate = 60;

export async function generateMetadata(): Promise<Metadata> {
  const page = await loadSitePage('home');
  if (!page) return { title: 'LiteShop' };
  return {
    title: page.seo.title,
    description: page.seo.description,
    keywords: page.seo.keywords,
    robots: page.seo.noIndex ? { index: false, follow: false } : undefined,
  };
}

export default async function HomePage(): Promise<JSX.Element> {
  const page = await loadSitePage('home');
  if (!page) return <main>页面不存在</main>;
  return <SiteRenderer page={page} />;
}
