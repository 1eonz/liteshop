import type { MetadataRoute } from 'next';

import { sitePages } from '../src/site-data';
import { loadSitePageSlugs } from '../src/site-data.server';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';
  const slugs = await loadSitePageSlugs();
  const knownSlugs = slugs.length ? slugs : Object.keys(sitePages);
  return knownSlugs.map((slug) => ({
    url: slug === 'home' ? baseUrl : `${baseUrl}/${slug}`,
    lastModified: new Date(),
    changeFrequency: slug === 'home' ? 'daily' : 'monthly',
    priority: slug === 'home' ? 1 : 0.7,
  }));
}
